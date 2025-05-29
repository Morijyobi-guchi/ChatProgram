import tkinter as tk
from tkinter import scrolledtext, simpledialog, PhotoImage, messagebox
import socket
import threading
import datetime

class ChatServerGUI:
    def __init__(self, master):
        self.master = master
        master.title("チャットサーバー")
        master.geometry("550x350") # 少しサイズ調整
        master.configure(bg='#ADD8E6') # Light Blue背景

        # アイコン設定 (オプション: .pngファイルを同じディレクトリに配置)
        try:
            icon = PhotoImage(file='server_icon.png') # ここにアイコンファイル名
            master.iconphoto(True, icon)
        except tk.TclError:
            print("サーバーアイコンが見つかりません。スキップします。")

        self.log_label = tk.Label(master, text="サーバーログ:", bg='#ADD8E6', font=("Arial", 12))
        self.log_label.pack(pady=(10,0))

        self.log_area = scrolledtext.ScrolledText(master, state='disabled', wrap=tk.WORD, height=15, width=65,
                                                  bg='#F0F0F0', fg='#333333', font=("Arial", 10)) # Light Grey BG, Dark Grey FG
        self.log_area.pack(pady=5, padx=10)

        self.button_frame = tk.Frame(master, bg='#ADD8E6')
        self.button_frame.pack(pady=10)

        self.start_button = tk.Button(self.button_frame, text="サーバー起動", command=self.start_server_prompt,
                           bg='#4CAF50', fg='white', font=("Arial", 10, "bold"), relief=tk.RAISED, borderwidth=3,
                           activebackground='#45a049') # Green BG
        self.start_button.pack(side=tk.LEFT, padx=20) # padxの値を増やして間隔を調整

        self.stop_button = tk.Button(self.button_frame, text="サーバー停止", command=self.stop_server, state='disabled',
                          bg='#F44336', fg='white', font=("Arial", 10, "bold"), relief=tk.RAISED, borderwidth=3,
                          activebackground='#e53935') # Red BG
        self.stop_button.pack(side=tk.LEFT, padx=20) # padxの値を増やして間隔を調整

        self.server_socket = None
        self.client_sockets = [] # (socket, address, username) のタプルを格納
        self.is_running = False
        self.listen_thread = None
        self.port = 50000 # デフォルトポート

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log_message(self, message, level="INFO"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{now}] [{level}] {message}\n"
        
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, formatted_message)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        print(formatted_message.strip())

    def start_server_prompt(self):
        port_str = simpledialog.askstring("ポート番号", "サーバーを起動するポート番号を入力してください:", initialvalue=str(self.port), parent=self.master)
        if port_str:
            try:
                self.port = int(port_str)
                if not (1024 <= self.port <= 65535):
                    messagebox.showerror("ポートエラー", "ポート番号は1024から65535の間で指定してください。", parent=self.master)
                    self.log_message("エラー: ポート番号は1024から65535の間で指定してください。", "ERROR")
                    return
                self.start_server_logic()
            except ValueError:
                messagebox.showerror("ポートエラー", "無効なポート番号です。", parent=self.master)
                self.log_message("エラー: 無効なポート番号です。", "ERROR")

    def start_server_logic(self):
        if self.is_running:
            self.log_message("サーバーは既に起動しています。", "WARN")
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(("", self.port))
            self.server_socket.listen()
            self.is_running = True
            self.log_message(f"サーバーがポート {self.port} で起動しました。")
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')

            self.listen_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.listen_thread.start()
        except Exception as e:
            self.log_message(f"サーバー起動エラー: {e}", "ERROR")
            messagebox.showerror("起動エラー", f"サーバー起動に失敗しました: {e}", parent=self.master)
            if self.server_socket:
                self.server_socket.close()
            self.is_running = False
            self.start_button.config(state='normal') # 失敗したらボタンを戻す

    def stop_server(self, show_log = True):
        if not self.is_running:
            if show_log: self.log_message("サーバーは起動していません。", "WARN")
            return

        self.is_running = False
        
        clients_to_remove = list(self.client_sockets)
        for client_info in clients_to_remove:
            client_sock, _, username = client_info
            try:
                client_sock.sendall("SERVER_SHUTDOWN".encode('utf-8'))
                client_sock.close()
            except Exception as e:
                self.log_message(f"クライアント {username} のソケットクローズエラー: {e}", "ERROR")
        self.client_sockets.clear()

        if self.server_socket:
            try:
                # accept()のブロッキングを解除するためにダミー接続
                # サーバーソケット自体を閉じる前に、自己接続で accept() から抜ける
                # サーバーソケットが None になる前に実行
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dummy_socket:
                    dummy_socket.settimeout(0.1) # タイムアウトを短く設定
                    dummy_socket.connect(("127.0.0.1", self.port))
            except:
                pass # 接続できなくても、acceptがブロックしていなければ問題ない
            finally:
                self.server_socket.close()
                self.server_socket = None

        if self.listen_thread and self.listen_thread.is_alive():
             self.listen_thread.join(timeout=0.5)

        if show_log: self.log_message("サーバーが停止しました。")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')

    def accept_connections(self):
        while self.is_running:
            try:
                if not self.server_socket: break # サーバーソケットが閉じられていたらループ終了
                client_socket, client_address = self.server_socket.accept()
                if not self.is_running:
                    client_socket.close()
                    break
                
                username_bytes = client_socket.recv(1024)
                if not username_bytes:
                    client_socket.close()
                    continue
                username = username_bytes.decode('utf-8').strip()
                
                if not username or username.upper() == "SERVER" or username.upper() == "SYSTEM":
                    username = f"User{client_address[1]}"
                    try:
                        client_socket.sendall(f"SYSTEM: ユーザー名が無効だったため、{username} に設定されました。".encode('utf-8'))
                    except Exception:
                        pass # 送信失敗は許容

                # ユーザー名重複チェック
                existing_usernames = [info[2] for info in self.client_sockets]
                original_username = username
                count = 1
                while username in existing_usernames:
                    username = f"{original_username}_{count}"
                    count += 1
                if original_username != username:
                     try:
                        client_socket.sendall(f"SYSTEM: ユーザー名 '{original_username}' は既に使用中のため、'{username}' に変更されました。".encode('utf-8'))
                     except Exception:
                        pass


                client_info = (client_socket, client_address, username)
                self.client_sockets.append(client_info)
                self.log_message(f"{username} ({client_address[0]}:{client_address[1]}) が接続しました。")
                self.broadcast_message(f"SYSTEM: {username} さんが入室しました。", None)

                handler_thread = threading.Thread(target=self.client_handler, args=(client_info,), daemon=True)
                handler_thread.start()
            except socket.error as e:
                if self.is_running:
                    self.log_message(f"接続受付エラー: {e}", "ERROR")
                break 
            except Exception as e:
                if self.is_running:
                     self.log_message(f"予期せぬ受付エラー: {e}", "ERROR")
                break

    def client_handler(self, client_info):
        client_socket, client_address, username = client_info
        
        while self.is_running:
            try:
                message_bytes = client_socket.recv(4096)
                if not message_bytes:
                    break
                
                message_str = message_bytes.decode('utf-8')

                if message_str.startswith("/w ") or message_str.startswith("/msg "):
                    parts = message_str.split(" ", 2)
                    if len(parts) < 3:
                        self.send_to_client(client_socket, "SYSTEM: 個人メッセージの形式が正しくありません。例: /w ユーザー名 メッセージ")
                        continue
                    recipient_username = parts[1]
                    pm_content = parts[2]
                    self.handle_private_message(client_info, recipient_username, pm_content)
                elif message_str.strip().lower() == "/users":
                    self.send_user_list(client_socket)
                else:
                    full_message = f"{username}: {message_str}"
                    self.log_message(f"受信 ({username}): {message_str}")
                    self.broadcast_message(full_message, client_socket)

            except ConnectionResetError:
                self.log_message(f"エラー: {username} ({client_address[0]}:{client_address[1]}) との接続がリセットされました。", "WARN")
                break
            except UnicodeDecodeError:
                self.log_message(f"エラー ({username}): メッセージのデコードに失敗しました。UTF-8形式のメッセージのみ対応しています。", "WARN")
                # 不正なバイト列を受信した場合、接続を切断することも検討
            except Exception as e:
                if self.is_running:
                    self.log_message(f"クライアントハンドラエラー ({username}): {e}", "ERROR")
                break
        
        if client_info in self.client_sockets:
            self.client_sockets.remove(client_info)
        try:
            client_socket.close()
        except Exception as e:
            self.log_message(f"ソケットクローズエラー ({username}): {e}", "ERROR")

        if self.is_running :
            self.log_message(f"{username} ({client_address[0]}:{client_address[1]}) が切断しました。")
            self.broadcast_message(f"SYSTEM: {username} さんが退室しました。", None)

    def send_to_client(self, client_socket, message_string):
        try:
            client_socket.sendall(message_string.encode('utf-8'))
        except Exception as e:
            # 送信失敗時の処理 (通常は client_handler のメインループで検知される)
            # ここで client_sockets から削除すると client_handler と競合する可能性があるので注意
            self.log_message(f"特定クライアントへの送信エラー: {e}", "ERROR")


    def handle_private_message(self, sender_info, recipient_username, message_content):
        sender_socket, _, sender_username = sender_info
        
        recipient_found = False
        for r_socket, _, r_uname in self.client_sockets:
            if r_uname == recipient_username:
                if r_socket == sender_socket: # 自分自身へのPM
                    self.send_to_client(sender_socket, f"SYSTEM: 自分自身に個人メッセージは送信できません。")
                    self.log_message(f"PM試行 ({sender_username} -> {recipient_username}): 自分自身", "INFO")
                else:
                    self.send_to_client(r_socket, f"(個人 from {sender_username}): {message_content}")
                    self.send_to_client(sender_socket, f"(個人 to {recipient_username}): {message_content}")
                    self.log_message(f"PM ({sender_username} -> {recipient_username}): {message_content}", "INFO")
                recipient_found = True
                break
        
        if not recipient_found:
            self.send_to_client(sender_socket, f"SYSTEM: ユーザー '{recipient_username}' は見つかりません。")
            self.log_message(f"PM失敗 ({sender_username} -> {recipient_username}): 宛先不明", "WARN")

    def send_user_list(self, client_socket):
        if not self.client_sockets:
            user_list_str = "SYSTEM: 現在接続中のユーザーはいません。"
        else:
            usernames = [info[2] for info in self.client_sockets]
            user_list_str = "SYSTEM: 接続中のユーザー: " + ", ".join(usernames)
        
        self.send_to_client(client_socket, user_list_str)
        self.log_message(f"ユーザーリスト要求を処理 ({[info[2] for info in self.client_sockets if info[0] == client_socket]})", "INFO")


    def broadcast_message(self, message_string, sender_socket):
        clients_to_remove = []
        for client_info_b in self.client_sockets:
            client_sock_b, _, username_b = client_info_b
            # sender_socket が None (システムメッセージ) または送信者自身でない場合に送信
            if sender_socket is None or client_sock_b != sender_socket:
                try:
                    client_sock_b.sendall(message_string.encode('utf-8'))
                except Exception as e:
                    self.log_message(f"ブロードキャストエラー ({username_b}): {e}", "ERROR")
                    # 送信に失敗したクライアントはリストから削除候補とする
                    # ただし、ここで直接削除すると client_handler と競合する可能性があるため、
                    # client_handler のエラー処理に任せるのが基本。
                    # ここではログのみに留めるか、より高度なエラーハンドリングが必要。
                    # clients_to_remove.append(client_info_b) # 今回は削除処理はclient_handlerに任せる
        
        # for dead_client in clients_to_remove:
        #     if dead_client in self.client_sockets:
        #         self.client_sockets.remove(dead_client)
        #         username_dead = dead_client[2]
        #         self.log_message(f"{username_dead} をリストから削除 (ブロードキャスト送信失敗)")
        #         # 再帰的なブロードキャストを避けるため、ここでは退室メッセージは送らない

    def on_closing(self):
        if self.is_running:
            if messagebox.askyesno("確認", "サーバーが実行中です。停止して終了しますか？", parent=self.master):
                self.stop_server(show_log=False) # 終了時はログを簡潔に
                self.master.destroy()
            else:
                return # 終了をキャンセル
        else:
            self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = ChatServerGUI(root)
    root.mainloop()
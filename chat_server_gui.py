import tkinter as tk
from tkinter import scrolledtext, simpledialog, PhotoImage
import socket
import threading
import datetime

class ChatServerGUI:
    def __init__(self, master):
        self.master = master
        master.title("チャットサーバー")
        master.geometry("500x400")

        # アイコン設定 (オプション: .pngファイルを同じディレクトリに配置)
        try:
            icon = PhotoImage(file='server_icon.png') # ここにアイコンファイル名
            master.iconphoto(True, icon)
        except tk.TclError:
            print("サーバーアイコンが見つかりません。スキップします。")


        self.log_area = scrolledtext.ScrolledText(master, state='disabled', wrap=tk.WORD, height=15, width=60)
        self.log_area.pack(pady=10, padx=10)

        self.start_button = tk.Button(master, text="サーバー起動", command=self.start_server_prompt)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(master, text="サーバー停止", command=self.stop_server, state='disabled')
        self.stop_button.pack(pady=5)

        self.server_socket = None
        self.client_sockets = [] # (socket, address, username) のタプルを格納
        self.is_running = False
        self.listen_thread = None
        self.port = 50000 # デフォルトポート [cite: 15, 24]

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log_message(self, message):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{now}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        print(f"[{now}] {message}")

    def start_server_prompt(self):
        port_str = simpledialog.askstring("ポート番号", "サーバーを起動するポート番号を入力してください:", initialvalue=str(self.port))
        if port_str:
            try:
                self.port = int(port_str)
                if not (1024 <= self.port <= 65535):
                    self.log_message("エラー: ポート番号は1024から65535の間で指定してください。")
                    return
                self.start_server_logic()
            except ValueError:
                self.log_message("エラー: 無効なポート番号です。")

    def start_server_logic(self):
        if self.is_running:
            self.log_message("サーバーは既に起動しています。")
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # [cite: 16, 24]
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(("", self.port)) # [cite: 24]
            self.server_socket.listen() # [cite: 24]
            self.is_running = True
            self.log_message(f"サーバーがポート {self.port} で起動しました。")
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')

            self.listen_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.listen_thread.start()
        except Exception as e:
            self.log_message(f"サーバー起動エラー: {e}")
            if self.server_socket:
                self.server_socket.close()
            self.is_running = False

    def stop_server(self):
        if not self.is_running:
            self.log_message("サーバーは起動していません。")
            return

        self.is_running = False # ループを停止させるフラグ
        
        # 既存のクライアント接続を閉じる
        # client_sockets は (socket, address, username) のリストなので注意
        clients_to_remove = list(self.client_sockets) # コピーを作成してイテレート
        for client_info in clients_to_remove:
            client_sock = client_info[0]
            try:
                client_sock.sendall("SERVER_SHUTDOWN".encode('utf-8'))
                client_sock.close()
            except Exception as e:
                self.log_message(f"クライアントソケットクローズエラー ({client_info[1]}): {e}")
        self.client_sockets.clear()

        # サーバーソケットを閉じる
        if self.server_socket:
            try:
                # accept()のブロッキングを解除するためにダミー接続を試みる
                # (より堅牢な方法はプラットフォーム依存のselectや非同期処理)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("127.0.0.1", self.port))
            except:
                pass # 接続できなくても問題ない
            finally:
                 self.server_socket.close() # [cite: 24]
                 self.server_socket = None


        if self.listen_thread and self.listen_thread.is_alive():
             self.listen_thread.join(timeout=1.0) # スレッドの終了を少し待つ

        self.log_message("サーバーが停止しました。")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')


    def accept_connections(self):
        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept() # [cite: 24]
                if not self.is_running: # 停止処理中なら抜ける
                    client_socket.close()
                    break
                
                # ユーザー名を受信 (最初のメッセージをユーザー名とする)
                username_bytes = client_socket.recv(1024) # [cite: 19]
                if not username_bytes:
                    client_socket.close()
                    continue
                username = username_bytes.decode('utf-8').strip()
                
                # ユーザー名が空または不正な場合はデフォルト名を付与
                if not username or username == "SERVER":
                    username = f"User{client_address[1]}"

                client_info = (client_socket, client_address, username)
                self.client_sockets.append(client_info)
                self.log_message(f"{username} ({client_address[0]}:{client_address[1]}) が接続しました。")
                self.broadcast_message(f"SYSTEM: {username} さんが入室しました。", None)

                handler_thread = threading.Thread(target=self.client_handler, args=(client_info,), daemon=True) # [cite: 38]
                handler_thread.start()
            except socket.error as e: # listenソケットが閉じられた場合のエラーを処理
                if self.is_running: # 意図しない停止の場合のみログ表示
                    self.log_message(f"接続受付エラー: {e}")
                break # ループを抜ける
            except Exception as e:
                if self.is_running:
                     self.log_message(f"予期せぬ受付エラー: {e}")
                break

    def client_handler(self, client_info):
        client_socket, client_address, username = client_info
        
        while self.is_running:
            try:
                message_bytes = client_socket.recv(4096) # [cite: 15] BUFSIZEに相当
                if not message_bytes: # 空のメッセージは切断とみなす
                    break
                
                # 実際のメッセージ処理は broadcast で行う
                full_message = f"{username}: {message_bytes.decode('utf-8')}"
                self.log_message(f"受信 ({username}): {message_bytes.decode('utf-8')}")
                self.broadcast_message(full_message, client_socket)

            except ConnectionResetError:
                self.log_message(f"エラー: {username} ({client_address[0]}:{client_address[1]}) との接続がリセットされました。")
                break
            except Exception as e:
                if self.is_running: # 意図しないエラーの場合のみログ
                    self.log_message(f"エラー ({username}): {e}")
                break
        
        # クライアント切断処理
        if client_info in self.client_sockets:
            self.client_sockets.remove(client_info)
        try:
            client_socket.close() # [cite: 15]
        except Exception as e:
            self.log_message(f"ソケットクローズエラー ({username}): {e}")

        if self.is_running : # サーバーがまだ動作中であれば退室メッセージを送信
            self.log_message(f"{username} ({client_address[0]}:{client_address[1]}) が切断しました。")
            self.broadcast_message(f"SYSTEM: {username} さんが退室しました。", None)


    def broadcast_message(self, message_string, sender_socket):
        # sender_socketがNoneの場合はシステムメッセージとして全員に送信
        clients_to_remove = []
        for client_info_b in self.client_sockets:
            client_sock_b = client_info_b[0]
            if client_sock_b != sender_socket:
                try:
                    client_sock_b.sendall(message_string.encode('utf-8')) # [cite: 24]
                except Exception as e:
                    self.log_message(f"ブロードキャストエラー ({client_info_b[2]}): {e}")
                    clients_to_remove.append(client_info_b)
        
        for dead_client in clients_to_remove:
            if dead_client in self.client_sockets:
                self.client_sockets.remove(dead_client)
                self.log_message(f"{dead_client[2]} をリストから削除 (送信失敗)")
                # 再帰的なブロードキャストを避けるため、ここでは退室メッセージは送らない
                # client_handler の切断処理に任せる

    def on_closing(self):
        if self.is_running:
            self.stop_server()
        self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = ChatServerGUI(root)
    root.mainloop()
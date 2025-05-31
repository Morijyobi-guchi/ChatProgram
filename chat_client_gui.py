import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, PhotoImage
import socket
import threading
import datetime
import re # 正規表現モジュールをインポート

class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("チャットクライアント")
        master.geometry("730x500") # サイズを少し調整
        master.configure(bg='#E0F7FA') # Light Cyan背景

        # アイコン設定 (オプション)
        try:
            icon = PhotoImage(file='client_icon.png')
            master.iconphoto(True, icon)
        except tk.TclError:
            print("クライアントアイコンが見つかりません。スキップします。")

        # 接続情報フレーム
        self.connection_frame = tk.Frame(master, bg='#B2EBF2', pady=5) # Lighter Cyan
        self.connection_frame.pack(fill=tk.X, padx=25, pady=(15,5)) # padxを25に増やしました

        self.host_label = tk.Label(self.connection_frame, text="サーバーIP:", bg='#B2EBF2', font=("Arial", 10))
        self.host_label.pack(side=tk.LEFT, padx=(10,0))
        self.host_entry = tk.Entry(self.connection_frame, width=15, font=("Arial", 10), relief=tk.SOLID, borderwidth=1)
        self.host_entry.insert(0, "localhost")
        self.host_entry.pack(side=tk.LEFT, padx=5)

        self.port_label = tk.Label(self.connection_frame, text="ポート:", bg='#B2EBF2', font=("Arial", 10))
        self.port_label.pack(side=tk.LEFT)
        self.port_entry = tk.Entry(self.connection_frame, width=7, font=("Arial", 10), relief=tk.SOLID, borderwidth=1)
        self.port_entry.insert(0, "50000")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.username_label = tk.Label(self.connection_frame, text="名前:", bg='#B2EBF2', font=("Arial", 10))
        self.username_label.pack(side=tk.LEFT)
        self.username_entry = tk.Entry(self.connection_frame, width=12, font=("Arial", 10), relief=tk.SOLID, borderwidth=1)
        self.username_entry.insert(0, f"User{datetime.datetime.now().second}")
        self.username_entry.pack(side=tk.LEFT, padx=5)

        self.connect_button = tk.Button(self.connection_frame, text="接続", command=self.connect_to_server,
                        bg='#4CAF50', fg='white', font=("Arial", 10, "bold"), relief=tk.RAISED, borderwidth=2, activebackground='#45a049',
                        width=8) # ボタンの幅を調整 (文字単位)
        self.connect_button.pack(side=tk.LEFT, padx=(20,20))
        
        self.disconnect_button = tk.Button(self.connection_frame, text="切断", command=self.disconnect_from_server, state='disabled',
                                           bg='#F44336', fg='white', font=("Arial", 10, "bold"), relief=tk.RAISED, borderwidth=2, activebackground='#e53935',width=8)
        self.disconnect_button.pack(side=tk.LEFT, padx=(0,20))

        # チャット表示エリア
        self.chat_display = scrolledtext.ScrolledText(master, state='disabled', wrap=tk.WORD, height=18, width=65,
                                                      bg='#FFFFFF', fg='#333333', font=("Arial", 10), relief=tk.SOLID, borderwidth=1)
        self.chat_display.pack(pady=5, padx=25, fill=tk.BOTH, expand=True) # padxを25に増やしました

        # メッセージ入力フレーム
        self.message_frame = tk.Frame(master, bg='#E0F7FA', pady=5)
        self.message_frame.pack(fill=tk.X, padx=25, pady=(5,15)) # padxを25に増やしました

        self.message_input = tk.Entry(self.message_frame, width=30, state='disabled', font=("Arial", 10), relief=tk.SOLID, borderwidth=1) # 55 * 0.7 = 38.5 -> 38 or 39
        self.message_input.pack(side=tk.LEFT, padx=(0,5), fill=tk.X, expand=True)
        self.message_input.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(self.message_frame, text="送信", command=self.send_message, state='disabled',
                                     bg='#2196F3', fg='white', font=("Arial", 10, "bold"), relief=tk.RAISED, borderwidth=2, activebackground='#1e88e5') # Blue
        self.send_button.pack(side=tk.LEFT, padx=(0,5))

        self.gemini_summarize_button = tk.Button(self.message_frame, text="Gemini要約", command=self.request_gemini_summary, state='disabled',
                                                 bg='#FFC107', fg='black', font=("Arial", 10, "bold"), relief=tk.RAISED, borderwidth=2, activebackground='#ffb300') # Amber
        self.gemini_summarize_button.pack(side=tk.LEFT)


        self.client_socket = None
        self.is_connected = False
        self.receive_thread = None
        self.username = "" # 接続時に設定される実際のユーザー名
        self.initial_username = "" # ユーザーが最初に入力したユーザー名

        # メッセージスタイル用タグ設定
        self.chat_display.tag_config('system', foreground='#00695C', font=("Arial", 10, 'italic')) # Teal
        self.chat_display.tag_config('system_error', foreground='#D32F2F', font=("Arial", 10, 'italic bold')) # Red
        self.chat_display.tag_config('system_warn', foreground='#FFA000', font=("Arial", 10, 'italic')) # Amber
        self.chat_display.tag_config('info', foreground='#0277BD', font=("Arial", 10, 'italic')) # Light Blue
        self.chat_display.tag_config('own_message', foreground='#0D47A1', font=("Arial", 10, 'bold')) # Dark Blue
        self.chat_display.tag_config('other_message', foreground='#333333') # Default Black/Grey
        self.chat_display.tag_config('pm_sent', foreground='#6A1B9A', font=("Arial", 10, 'italic')) # Purple (to X)
        self.chat_display.tag_config('pm_received', foreground='#AD1457', font=("Arial", 10, 'bold')) # Pink (from X)
        # self.chat_display.tag_config('summary', foreground='#4A148C', font=("Arial", 10, 'italic'), background='#E1BEE7') # 通常の要約用 (もしあれば)
        self.chat_display.tag_config('gemini_summary', foreground='#BF360C', font=("Arial", 10, 'italic'), background='#FFCCBC') # Deep Orange BG for Gemini summary


        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def display_message(self, message, tag=None):
        self.chat_display.config(state='normal')
        if tag:
            self.chat_display.insert(tk.END, message + "\n", tag)
        else:
            self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def connect_to_server(self):
        if self.is_connected:
            messagebox.showwarning("接続済み", "既にサーバーに接続しています。", parent=self.master)
            return

        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        self.initial_username = self.username_entry.get().strip() # ユーザーが入力した名前を保持
        self.username = self.initial_username # 初期値として設定

        if not host or not port_str or not self.username:
            messagebox.showerror("入力エラー", "サーバーIP、ポート、およびユーザー名を入力してください。", parent=self.master)
            return
        
        # クライアント側での予約語チェックはサーバーに任せても良いが、基本的なものは残す
        if self.username.upper() == "SERVER" or self.username.upper() == "SYSTEM":
            messagebox.showerror("入力エラー", "そのユーザー名は使用できません。", parent=self.master)
            return

        try:
            port = int(port_str)
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            
            self.client_socket.sendall(self.username.encode('utf-8')) # 最初にユーザー名を送信

            self.is_connected = True
            self.display_message(f"システム: {host}:{port} に接続試行中 (ユーザー名: {self.username})...", tag='info')
            self.master.title(f"チャットクライアント - {self.username}")

            self.connect_button.config(state='disabled')
            self.disconnect_button.config(state='normal')
            self.host_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.username_entry.config(state='disabled')
            self.message_input.config(state='normal')
            self.send_button.config(state='normal')
            # self.summarize_button.config(state='normal') # 通常の要約ボタン (もしあれば)
            self.gemini_summarize_button.config(state='normal') # Gemini要約ボタンを有効化
            self.message_input.focus_set()

            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()

        except ConnectionRefusedError:
            self.display_message("接続失敗: サーバーに接続できませんでした。IPとポートを確認してください。", tag='system_error')
            messagebox.showerror("接続失敗", "サーバーに接続できませんでした。サーバーが起動しているか、IPとポートを確認してください。", parent=self.master)
            self.client_socket = None
        except ValueError:
            self.display_message("ポートエラー: ポート番号が不正です。", tag='system_error')
            messagebox.showerror("ポートエラー", "ポート番号が不正です。", parent=self.master)
            self.client_socket = None
        except Exception as e:
            self.display_message(f"接続エラー: {e}", tag='system_error')
            messagebox.showerror("接続エラー", f"エラーが発生しました: {e}", parent=self.master)
            if self.client_socket:
                self.client_socket.close()
            self.client_socket = None
            
    def disconnect_from_server(self, show_info=True, reason=None):
        if not self.is_connected and not self.client_socket:
             if show_info and self.connect_button['state'] == 'normal':
                  pass
             elif show_info:
                  messagebox.showinfo("切断", "既にサーバーから切断されています。", parent=self.master)
             return

        self.is_connected = False
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError: pass # ソケットが既に閉じている場合など
            except Exception as e:
                print(f"ソケットクローズエラー: {e}")
            finally:
                self.client_socket = None

        # receive_thread の終了を待つ (is_connectedがFalseになればループは抜けるはず)
        # if self.receive_thread and self.receive_thread.is_alive():
        #    self.receive_thread.join(timeout=0.1) # 短いタイムアウト

        if show_info:
            msg = reason if reason else "サーバーから切断しました。"
            self.display_message(f"システム: {msg}", tag='info')
            messagebox.showinfo("切断完了", msg, parent=self.master)
        
        self.master.title("チャットクライアント")
        self.connect_button.config(state='normal')
        self.disconnect_button.config(state='disabled')
        self.host_entry.config(state='normal')
        self.port_entry.config(state='normal')
        self.username_entry.config(state='normal')
        self.message_input.config(state='disabled')
        self.send_button.config(state='disabled')
        # self.summarize_button.config(state='disabled') # 通常の要約ボタン (もしあれば)
        self.gemini_summarize_button.config(state='disabled') # Gemini要約ボタンを無効化
        self.message_input.delete(0, tk.END)


    def send_message_event(self, event=None):
        self.send_message()

    def send_message(self):
        if not self.is_connected or not self.client_socket:
            messagebox.showerror("送信エラー", "サーバーに接続されていません。", parent=self.master)
            return

        message = self.message_input.get().strip()
        if message:
            try:
                self.client_socket.sendall(message.encode('utf-8'))
                # コマンドでない通常のチャットメッセージの場合、ローカルエコーする
                # サーバーは送信者本人にはブロードキャストしないため
                if not message.startswith("/"):
                    self.display_message(f"{self.username}: {message}", tag='own_message')
                self.message_input.delete(0, tk.END)
            except BrokenPipeError:
                 self.handle_disconnection("送信エラー: サーバーとの接続が切れました。(BrokenPipe)")
            except ConnectionResetError:
                 self.handle_disconnection("送信エラー: サーバーとの接続がリセットされました。(ConnectionReset)")
            except Exception as e:
                self.handle_disconnection(f"送信エラー: {e}")

    # def request_summary(self): # 通常の要約リクエスト (もしあれば)
    #     if not self.is_connected or not self.client_socket:
    #         messagebox.showerror("要約エラー", "サーバーに接続されていません。", parent=self.master)
    #         return
    #     try:
    #         self.client_socket.sendall("/summarize".encode('utf-8'))
    #         self.display_message("システム: チャットの要約をリクエストしました...", tag='info')
    #     except BrokenPipeError:
    #         self.handle_disconnection("要約リクエストエラー: サーバーとの接続が切れました。(BrokenPipe)")
    #     except ConnectionResetError:
    #         self.handle_disconnection("要約リクエストエラー: サーバーとの接続がリセットされました。(ConnectionReset)")
    #     except Exception as e:
    #         self.handle_disconnection(f"要約リクエストエラー: {e}")

    def request_gemini_summary(self):
        if not self.is_connected or not self.client_socket:
            messagebox.showerror("Gemini要約エラー", "サーバーに接続されていません。", parent=self.master)
            return
        try:
            self.client_socket.sendall("/summarize_gemini".encode('utf-8'))
            self.display_message("システム: Gemini要約をリクエストしました...", tag='info')
        except BrokenPipeError:
            self.handle_disconnection("Gemini要約リクエストエラー: サーバーとの接続が切れました。(BrokenPipe)")
        except ConnectionResetError:
            self.handle_disconnection("Gemini要約リクエストエラー: サーバーとの接続がリセットされました。(ConnectionReset)")
        except Exception as e:
            self.handle_disconnection(f"Gemini要約リクエストエラー: {e}")


    def receive_messages(self):
        while self.is_connected and self.client_socket:
            try:
                message_bytes = self.client_socket.recv(4096)
                if not message_bytes:
                    self.handle_disconnection("サーバーが接続を閉じました。")
                    break
                
                message = message_bytes.decode('utf-8')

                # ユーザー名変更通知の処理
                # 例: "SYSTEM: ユーザー名 'User1' は既に使用中のため、'User1_1' に変更されました。"
                # 例: "SYSTEM: ユーザー名が無効だったため、'User12345' に設定されました。"
                match_rename = re.match(r"SYSTEM: ユーザー名 '(.*)' は既に使用中のため、'(.*)' に変更されました。", message)
                match_setname = re.match(r"SYSTEM: ユーザー名が無効だったため、'(.*)' に設定されました。", message)

                if match_rename and match_rename.group(1) == self.initial_username:
                    old_name, new_name = match_rename.groups()
                    self.username = new_name
                    self.master.title(f"チャットクライアント - {self.username}")
                    self.display_message(message, tag='system_warn')
                elif match_setname and self.is_connected : # 接続直後の可能性が高い
                    # この形式の場合、誰のユーザー名が変更されたか特定しにくいが、
                    # 接続直後であれば自分の可能性が高い。
                    # より確実なのはサーバーが「あなたのユーザー名は～」と送ること。
                    # ここでは、もしinitial_usernameがサーバーによって不適切と判断された場合を想定。
                    new_name = match_setname.group(1)
                    # 最初のユーザー名が空だったり予約語だった場合、このメッセージが飛んでくる
                    if self.initial_username == "" or self.initial_username.upper() == "SERVER" or self.initial_username.upper() == "SYSTEM" or self.initial_username == new_name : # 最後の条件は、元々その名前だった場合
                        self.username = new_name
                        self.master.title(f"チャットクライアント - {self.username}")
                        self.display_message(message, tag='system_warn')
                    else: # 他の誰かの名前が設定されたメッセージかもしれない
                        self.display_message(message, tag='system')

                elif message == "SERVER_SHUTDOWN":
                    self.handle_disconnection("サーバーがシャットダウンしました。")
                    break
                elif message.startswith("SYSTEM_INFO:"): # サーバーからのお知らせ (例: 要約生成中)
                    self.display_message(message, tag='info')
                elif message.startswith("SYSTEM:"):
                    self.display_message(message, tag='system')
                elif message.startswith("(個人 from"): # (個人 from Sender): Message
                    self.display_message(message, tag='pm_received')
                elif message.startswith("(個人 to"):   # (個人 to Recipient): Message
                    self.display_message(message, tag='pm_sent')
                # elif message.startswith("SYSTEM_SUMMARY:"): # 通常の要約メッセージ (もしあれば)
                #     self.display_message(message, tag='summary')
                elif message.startswith("SYSTEM_GEMINI_SUMMARY:"): # Gemini要約メッセージ
                    # ライブラリ未インストールエラーの特別処理
                    if "ライブラリがインストールされていない" in message:
                        self.display_message("システム: Google Generative AIライブラリがサーバーにインストールされていません。", tag='system_error')
                        self.display_message("システム: 管理者にライブラリのインストールを依頼してください。", tag='system_error')
                        self.display_message("システム: インストールコマンド: pip install google-generativeai", tag='info')
                    elif "APIが利用できない" in message:
                        self.display_message("システム: Gemini APIが設定されていないか、初期化に失敗しました。", tag='system_error')
                    else:
                        self.display_message(message, tag='gemini_summary')
                else:
                    self.display_message(message, tag='other_message')

            except UnicodeDecodeError:
                self.display_message("受信エラー: メッセージのデコードに失敗しました。", tag='system_error')
            except ConnectionResetError:
                if self.is_connected:
                    self.handle_disconnection("サーバーとの接続がリセットされました。")
                break
            except ConnectionAbortedError:
                if self.is_connected:
                    self.handle_disconnection("サーバーとの接続が中断されました。")
                break
            except OSError: # ソケットが閉じられた後など
                 if self.is_connected:
                      self.handle_disconnection("受信エラー (OSError)")
                 break
            except Exception as e:
                if self.is_connected:
                    self.handle_disconnection(f"受信エラー: {e}")
                break
    
    def handle_disconnection(self, reason_message):
        if self.is_connected :
            self.is_connected = False # これで receive_messages ループも止まる
            # GUI操作はメインスレッドで行う
            self.master.after(0, lambda: self.disconnect_from_server(show_info=True, reason=reason_message))

    def on_closing(self):
        if self.is_connected:
            # 確認ダイアログを出すか、即座に切断するかは設計による
            # if messagebox.askyesno("終了確認", "サーバーに接続中です。切断して終了しますか？", parent=self.master):
            #    self.disconnect_from_server(show_info=False)
            #    self.master.destroy()
            # else:
            #    return # 終了をキャンセル
            self.disconnect_from_server(show_info=False) # ここでは確認なしで即時切断
        self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()
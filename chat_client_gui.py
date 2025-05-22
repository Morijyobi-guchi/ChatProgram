import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, PhotoImage
import socket
import threading
import datetime

class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("チャットクライアント")
        master.geometry("500x450")

        # アイコン設定 (オプション)
        try:
            icon = PhotoImage(file='client_icon.png') # ここにアイコンファイル名
            master.iconphoto(True, icon)
        except tk.TclError:
            print("クライアントアイコンが見つかりません。スキップします。")

        self.connection_frame = tk.Frame(master)
        self.connection_frame.pack(pady=5)

        self.host_label = tk.Label(self.connection_frame, text="サーバーIP:")
        self.host_label.pack(side=tk.LEFT)
        self.host_entry = tk.Entry(self.connection_frame, width=15)
        self.host_entry.insert(0, "localhost") # [cite: 15] デフォルトはlocalhost
        self.host_entry.pack(side=tk.LEFT, padx=5)

        self.port_label = tk.Label(self.connection_frame, text="ポート:")
        self.port_label.pack(side=tk.LEFT)
        self.port_entry = tk.Entry(self.connection_frame, width=7)
        self.port_entry.insert(0, "50000") # [cite: 15] デフォルトポート
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.username_label = tk.Label(self.connection_frame, text="名前:")
        self.username_label.pack(side=tk.LEFT)
        self.username_entry = tk.Entry(self.connection_frame, width=10)
        self.username_entry.insert(0, f"User{datetime.datetime.now().second}") # 簡単なデフォルト名
        self.username_entry.pack(side=tk.LEFT, padx=5)


        self.connect_button = tk.Button(self.connection_frame, text="接続", command=self.connect_to_server)
        self.connect_button.pack(side=tk.LEFT)
        
        self.disconnect_button = tk.Button(self.connection_frame, text="切断", command=self.disconnect_from_server, state='disabled')
        self.disconnect_button.pack(side=tk.LEFT, padx=5)


        self.chat_display = scrolledtext.ScrolledText(master, state='disabled', wrap=tk.WORD, height=15, width=60)
        self.chat_display.pack(pady=10, padx=10)

        self.message_frame = tk.Frame(master)
        self.message_frame.pack(pady=5)

        self.message_input = tk.Entry(self.message_frame, width=50, state='disabled')
        self.message_input.pack(side=tk.LEFT, padx=5)
        self.message_input.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(self.message_frame, text="送信", command=self.send_message, state='disabled')
        self.send_button.pack(side=tk.LEFT)

        self.client_socket = None
        self.is_connected = False
        self.receive_thread = None
        self.username = ""

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END) # 最新のメッセージが見えるようにスクロール
        self.chat_display.config(state='disabled')

    def connect_to_server(self):
        if self.is_connected:
            messagebox.showwarning("接続済み", "既にサーバーに接続しています。")
            return

        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        self.username = self.username_entry.get().strip()

        if not host or not port_str or not self.username:
            messagebox.showerror("入力エラー", "サーバーIP、ポート、およびユーザー名を入力してください。")
            return
        
        if self.username == "SERVER" or self.username.lower() == "system": # 予約語チェック
            messagebox.showerror("入力エラー", "そのユーザー名は使用できません。")
            return

        try:
            port = int(port_str)
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # [cite: 16]
            self.client_socket.connect((host, port)) # [cite: 15]
            
            # 最初にユーザー名を送信
            self.client_socket.sendall(self.username.encode('utf-8'))

            self.is_connected = True
            self.display_message(f"システム: {host}:{port} (ユーザー名: {self.username}) に接続しました。")

            self.connect_button.config(state='disabled')
            self.disconnect_button.config(state='normal')
            self.host_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.username_entry.config(state='disabled')
            self.message_input.config(state='normal')
            self.send_button.config(state='normal')

            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True) # [cite: 46] daemon=Trueでメイン終了時にスレッドも終了
            self.receive_thread.start()

        except ConnectionRefusedError:
            messagebox.showerror("接続失敗", "サーバーに接続できませんでした。サーバーが起動しているか、IPとポートを確認してください。")
            self.client_socket = None
        except ValueError:
            messagebox.showerror("ポートエラー", "ポート番号が不正です。")
            self.client_socket = None
        except Exception as e:
            messagebox.showerror("接続エラー", f"エラーが発生しました: {e}")
            if self.client_socket:
                self.client_socket.close()
            self.client_socket = None
            
    def disconnect_from_server(self, show_info=True):
        if not self.is_connected and not self.client_socket: # 既に切断済みの場合
             if show_info and self.connect_button['state'] == 'normal': # 初回起動時など
                  pass # 何もしない
             elif show_info: # 明示的な切断操作だが既に切断されている場合
                  messagebox.showinfo("切断", "既にサーバーから切断されています。")
             return

        self.is_connected = False # これでreceive_messagesループが止まる
        if self.client_socket:
            try:
                # サーバーに切断を通知するようなメッセージは、サーバー側の設計による
                # ここではソケットを閉じるだけ
                self.client_socket.shutdown(socket.SHUT_RDWR) # 送受信を即時停止
                self.client_socket.close() # [cite: 15]
            except OSError as e: # (例:ソケットが既に閉じている場合など)
                print(f"ソケットクローズ中のOSエラー: {e}")
            except Exception as e:
                print(f"ソケットクローズエラー: {e}")
            finally:
                self.client_socket = None

        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=0.5) # スレッドの終了を少し待つ

        if show_info:
            self.display_message("システム: サーバーから切断しました。")
            messagebox.showinfo("切断完了", "サーバーから切断しました。")

        self.connect_button.config(state='normal')
        self.disconnect_button.config(state='disabled')
        self.host_entry.config(state='normal')
        self.port_entry.config(state='normal')
        self.username_entry.config(state='normal')
        self.message_input.config(state='disabled')
        self.send_button.config(state='disabled')
        self.message_input.delete(0, tk.END)


    def send_message_event(self, event=None): # Enterキーでの送信
        self.send_message()

    def send_message(self):
        if not self.is_connected or not self.client_socket:
            messagebox.showerror("送信エラー", "サーバーに接続されていません。")
            return

        message = self.message_input.get().strip()
        if message:
            try:
                self.client_socket.sendall(message.encode('utf-8')) # [cite: 19]
                # 自分自身のメッセージはサーバーからのブロードキャストで表示される
                # self.display_message(f"自分: {message}") # ローカルエコーする場合
                self.message_input.delete(0, tk.END)
            except BrokenPipeError:
                 self.handle_disconnection("送信エラー: サーバーとの接続が切れました。(BrokenPipe)")
            except ConnectionResetError:
                 self.handle_disconnection("送信エラー: サーバーとの接続がリセットされました。(ConnectionReset)")
            except Exception as e:
                self.handle_disconnection(f"送信エラー: {e}")


    def receive_messages(self):
        while self.is_connected and self.client_socket:
            try:
                message_bytes = self.client_socket.recv(4096) # [cite: 15] BUFSIZEに相当
                if not message_bytes: # サーバーがソケットを閉じた場合
                    self.handle_disconnection("サーバーが接続を閉じました。")
                    break
                
                message = message_bytes.decode('utf-8')
                if message == "SERVER_SHUTDOWN":
                    self.handle_disconnection("サーバーがシャットダウンしました。")
                    break
                else:
                    self.display_message(message)

            except ConnectionResetError:
                if self.is_connected: # 意図しない切断の場合のみ
                    self.handle_disconnection("サーバーとの接続がリセットされました。")
                break
            except ConnectionAbortedError:
                if self.is_connected:
                    self.handle_disconnection("サーバーとの接続が中断されました。")
                break
            except OSError as e: # (例:ソケットが閉じられた後など)
                 if self.is_connected:
                      self.handle_disconnection(f"受信エラー (OSError): {e}")
                 break
            except Exception as e: # その他の予期せぬエラー
                if self.is_connected:
                    self.handle_disconnection(f"受信エラー: {e}")
                break
        # is_connected が False になったらスレッドは終了
    
    def handle_disconnection(self, reason_message):
        if self.is_connected : # 複数回呼ばれるのを防ぐ
            self.is_connected = False # これで receive_messages ループも止まる
            self.master.after(0, lambda: messagebox.showinfo("切断", reason_message)) # GUIスレッドでダイアログ表示
            self.master.after(0, lambda: self.disconnect_from_server(show_info=False)) # GUIスレッドで切断処理

    def on_closing(self):
        if self.is_connected:
            self.disconnect_from_server(show_info=False)
        self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()
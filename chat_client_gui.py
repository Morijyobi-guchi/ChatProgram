import customtkinter as ctk
from tkinter import messagebox, PhotoImage  # messagebox と PhotoImage は tkinter から継続利用
import socket
import threading
import datetime
import re # 正規表現モジュールをインポート
import os
import sys

# リソースパスを取得する関数
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("チャットクライアント")
        master.geometry("680x500")

        ctk.set_appearance_mode("Light")  # Modes: "System" (default), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

        # アイコン設定 (ICO優先, PNGフォールバック)
        try:
            icon_path = get_resource_path('positto.ico')
            master.wm_iconbitmap(icon_path)
        except Exception as e:
            print(f"ICOアイコン設定中にエラーが発生: {e}")
            try:
                icon_img_path = get_resource_path('client_icon.png')
                icon = PhotoImage(file=icon_img_path)
                
                # アイコンのサイズを調整（32x32または16x16が推奨）
                # subsampleで縮小する場合
                # icon = icon.subsample(2, 2)  # 半分のサイズに縮小
                
                # ウィンドウのアイコンを設定
                master.iconphoto(True, icon)
                
                # 追加の設定（Windows用）
                master.wm_iconphoto(True, icon)
                
                print("アイコンを正常に設定しました: client_icon.png")
                
            except Exception as e2:
                print(f"PNGアイコン設定中にエラーが発生: {e2}\nサポートされる形式: ICO (推奨), PNG, GIF")
                # photo(default, *photoimages)の説明:
                # - default=True: このアイコンをアプリケーションのデフォルトアイコンとして設定
                #   True: 全ての新しいトップレベルウィンドウに適用
                #   False: このウィンドウのみに適用
                # - icon: PhotoImageオブジェクト（PNG、GIF形式をサポート）
                # 
                # 効果:
                # 1. ウィンドウのタイトルバー左端にアイコンが表示される
                # 2. タスクバーにアイコンが表示される
                # 3. Alt+Tabでのウィンドウ切り替え時にアイコンが表示される
                # 4. システムの通知エリアでアイコンが使用される
                master.iconphoto(True, icon)
                
                print("アイコンを正常に設定しました: client_icon.png")
        except FileNotFoundError:
            print("アイコンファイルが見つかりません: client_icon.png または client_icon.ico")
            print("デフォルトのTkinterアイコンを使用します")
        except Exception as e:
            print(f"アイコン設定中にエラーが発生: {e}")
            print("サポートされる形式: PNG, GIF")

        # 接続情報フレーム
        self.connection_frame = ctk.CTkFrame(master, fg_color="transparent")
        self.connection_frame.pack(fill="x", padx=25, pady=(15,5))

        self.host_label = ctk.CTkLabel(self.connection_frame, text="サーバーIP:")
        self.host_label.pack(side="left", padx=(5,0))
        self.host_entry = ctk.CTkEntry(self.connection_frame, width=110)
        self.host_entry.insert(0, "localhost")
        self.host_entry.pack(side="left", padx=5)

        self.port_label = ctk.CTkLabel(self.connection_frame, text="ポート:")
        self.port_label.pack(side="left")
        self.port_entry = ctk.CTkEntry(self.connection_frame, width=50)
        self.port_entry.insert(0, "50000")
        self.port_entry.pack(side="left", padx=5)
        
        self.username_label = ctk.CTkLabel(self.connection_frame, text="名前:")
        self.username_label.pack(side="left")
        self.username_entry = ctk.CTkEntry(self.connection_frame, width=70)
        self.username_entry.insert(0, f"User{datetime.datetime.now().second}")
        self.username_entry.pack(side="left", padx=5)

        self.connect_button = ctk.CTkButton(self.connection_frame, text="接続", command=self.connect_to_server, width=70)
        self.connect_button.pack(side="left", padx=(0,5))
        
        self.disconnect_button = ctk.CTkButton(self.connection_frame, text="切断", command=self.disconnect_from_server, state='disabled', width=70)
        self.disconnect_button.pack(side="left", padx=(0,10))

        self.help_button = ctk.CTkButton(self.connection_frame, text="ヘルプ", command=self.show_help, width=70, fg_color=("#4CAF50", "#45a049"))
        self.help_button.pack(side="left", padx=(0,5))

        # チャット表示エリア（LINEライクなレイアウト）
        self.chat_display = ctk.CTkScrollableFrame(master, fg_color="#f0f0f0")
        self.chat_display.pack(pady=5, padx=25, fill="both", expand=True)

        # メッセージ入力フレーム
        self.message_frame = ctk.CTkFrame(master, fg_color="transparent")
        self.message_frame.pack(fill="x", padx=80, pady=(5,15))

        self.message_input = ctk.CTkEntry(self.message_frame, state='disabled', placeholder_text="メッセージを入力...")
        self.message_input.pack(side="left", padx=(0,5), fill="x", expand=True)
        self.message_input.bind("<Return>", self.send_message_event)

        self.send_button = ctk.CTkButton(self.message_frame, text="送信", command=self.send_message, state='disabled', width=60)
        self.send_button.pack(side="left", padx=(0,5))

        self.ai_positive_active = False # AIポジティブモードの状態フラグ
        self.ai_positive_button = ctk.CTkButton(
            self.message_frame, 
            text="ポジティブ", 
            state='disabled', 
            width=120, 
            command=self.handle_ai_positive_click
        )
        self.ai_positive_button.pack(side="left", padx=(5,0))
        
        self.client_socket = None
        self.is_connected = False
        self.receive_thread = None
        self.username = "" # 接続時に設定される実際のユーザー名
        self.initial_username = "" # ユーザーが最初に入力したユーザー名

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_message_bubble(self, username, message_text, is_own=False, message_type="normal"):
        """LINEライクなメッセージバブルを作成"""
        # メッセージコンテナフレーム
        container = ctk.CTkFrame(self.chat_display, fg_color="transparent")
        container.pack(fill="x", padx=10, pady=2)
        
        if message_type == "system":
            # システムメッセージは中央配置
            system_frame = ctk.CTkFrame(container, fg_color="#ffebee", corner_radius=15)
            system_frame.pack(pady=5)
            system_label = ctk.CTkLabel(
                system_frame, 
                text=message_text, 
                text_color="#d32f2f",
                font=("Arial", 15, "bold"),  # 太字を追加
                wraplength=400
            )
            system_label.pack(padx=10, pady=5)
        else:
            if is_own:
                # 自分のメッセージ（右側）
                message_frame = ctk.CTkFrame(container, fg_color="transparent")
                message_frame.pack(side="right", anchor="e")
                
                bubble = ctk.CTkFrame(message_frame, fg_color="#e3f2fd", corner_radius=15)
                bubble.pack(side="right", padx=(50, 0))
                
                # メッセージテキスト
                message_label = ctk.CTkLabel(
                    bubble, 
                    text=message_text, 
                    text_color="#000000",
                    font=("Arial", 16, "bold"),  # 太字を追加
                    wraplength=300,
                    justify="left"
                )
                message_label.pack(anchor="e", padx=10, pady=(5, 5))
            else:
                # 相手のメッセージ（左側）
                message_frame = ctk.CTkFrame(container, fg_color="transparent")
                message_frame.pack(side="left", anchor="w")
                
                # ユーザー名表示（バブルの外側上部）
                if username and ":" in f"{username}:":
                    display_name = username.split(":")[0] if ":" in username else username
                    name_label = ctk.CTkLabel(
                        message_frame, 
                        text=display_name, 
                        font=("Arial", 13, "bold"),  # 太字を追加
                        text_color="#666"
                    )
                    name_label.pack(anchor="w", padx=10, pady=(0, 2))
                
                bubble = ctk.CTkFrame(message_frame, fg_color="#ffffff", corner_radius=15)
                bubble.pack(side="left", padx=(0, 50))
                
                # メッセージテキスト
                clean_message = message_text
                if ":" in message_text and username:
                    parts = message_text.split(":", 1)
                    if len(parts) > 1:
                        clean_message = parts[1].strip()
                
                message_label = ctk.CTkLabel(
                    bubble, 
                    text=clean_message, 
                    text_color="#000000",
                    font=("Arial", 16, "bold"),  # 太字を追加
                    wraplength=300,
                    justify="left"
                )
                message_label.pack(anchor="w", padx=10, pady=5)
        
        # スクロールを最下部に移動
        self.chat_display._parent_canvas.after(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """チャット表示を最下部にスクロール"""
        self.chat_display._parent_canvas.yview_moveto(1.0)

    def display_message(self, message, tag=None):
        """メッセージを表示（新しいバブル形式）"""
        # メッセージの種類を判定
        if tag in ['system', 'system_error', 'system_warn', 'info']:
            self.create_message_bubble("", message, False, "system")
        elif tag == 'own_message':
            # 自分のメッセージ
            self.create_message_bubble(self.username, message, True)
        elif tag in ['pm_sent', 'pm_received']:
            # 個人メッセージ
            self.create_message_bubble("", message, tag == 'pm_sent', "system")
        else:
            # 他のユーザーのメッセージ
            username = ""
            clean_message = message
            if ":" in message and not message.startswith("SYSTEM:"):
                parts = message.split(":", 1)
                if len(parts) > 1:
                    username = parts[0].strip()
                    clean_message = parts[1].strip()
            
            is_own = (username == self.username)
            self.create_message_bubble(username, clean_message, is_own)

    def connect_to_server(self):
        if self.is_connected:
            messagebox.showwarning("接続済み", "既にサーバーに接続しています。", parent=self.master)
            return

        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        self.initial_username = self.username_entry.get().strip()
        self.username = self.initial_username

        if not host or not port_str or not self.username:
            messagebox.showerror("入力エラー", "サーバーIP、ポート、およびユーザー名を入力してください。", parent=self.master)
            return
        
        if self.username.upper() == "SERVER" or self.username.upper() == "SYSTEM":
            messagebox.showerror("入力エラー", "そのユーザー名は使用できません。", parent=self.master)
            return

        try:
            port = int(port_str)
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            
            self.client_socket.sendall(self.username.encode('utf-8'))

            self.is_connected = True
            self.display_message(f"システム: {host}:{port} に接続試行中 (ユーザー名: {self.username})...", tag='info')
            self.master.title(f"チャットクライアント - {self.username}")

            self.connect_button.configure(state='disabled')
            self.disconnect_button.configure(state='normal')
            self.host_entry.configure(state='disabled')
            self.port_entry.configure(state='disabled')
            self.username_entry.configure(state='disabled')
            self.message_input.configure(state='normal')
            self.send_button.configure(state='normal')
            # self.ask_gemini_button.configure(state='normal') # 変更
            # self.ask_gemini_button.configure(text="Gemini応答OFF", fg_color=("#FF9800", "#E67E00")) # 変更
            # self.gemini_mode_enabled = False # 変更
            self.ai_positive_button.configure(state='normal', text="ポジティブ") # 状態更新
            self.ai_positive_active = False # 状態更新
            self.message_input.focus()

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
             if show_info and self.connect_button.cget('state') == 'normal':
                  pass
             elif show_info:
                  messagebox.showinfo("切断", "既にサーバーから切断されています。", parent=self.master)
             return

        self.is_connected = False
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError: pass
            except Exception as e:
                print(f"ソケットクローズエラー: {e}")
            finally:
                self.client_socket = None

        if show_info:
            msg = reason if reason else "サーバーから切断しました。"
            self.display_message(f"システム: {msg}", tag='info')

        
        self.master.title("チャットクライアント")
        self.connect_button.configure(state='normal')
        self.disconnect_button.configure(state='disabled')
        self.host_entry.configure(state='normal')
        self.port_entry.configure(state='normal')
        self.username_entry.configure(state='normal')
        self.message_input.configure(state='disabled')
        self.send_button.configure(state='disabled')
        # self.ask_gemini_button.configure(state='disabled') # 変更
        # self.ask_gemini_button.configure(text="Gemini応答OFF", fg_color=("#FF9800", "#E67E00")) # 変更
        # self.gemini_mode_enabled = False # 変更
        self.ai_positive_button.configure(state='disabled', text="ポジティブ", fg_color=("#808080", "#606060")) # 状態更新
        self.ai_positive_active = False # 状態更新
        self.message_input.delete(0, "end")

    def send_message_event(self, event=None):
        self.send_message()

    def send_message(self):
        if not self.is_connected or not self.client_socket:
            messagebox.showerror("送信エラー", "サーバーに接続されていません。", parent=self.master)
            return

        message = self.message_input.get().strip()
        if message:
            try:
                if self.ai_positive_active: # AIポジティブモードが有効な場合
                    self.client_socket.sendall(f"/positive_transform {message}".encode('utf-8'))
                elif message.startswith("/"):
                    self.client_socket.sendall(message.encode('utf-8'))
                    if message.lower().startswith("/w ") or message.lower().startswith("/msg "):
                        pass
                    elif message.lower() == "/users":
                        pass
                    else:
                        self.display_message(f"コマンド送信: {message}", tag='info')
                else:
                    self.client_socket.sendall(message.encode('utf-8'))
                    self.display_message(message, tag='own_message')  # ユーザー名を除去してメッセージのみ表示
                
                self.message_input.delete(0, "end")
            except BrokenPipeError:
                 self.handle_disconnection("送信エラー: サーバーとの接続が切れました。(BrokenPipe)")
            except ConnectionResetError:
                 self.handle_disconnection("送信エラー: サーバーとの接続がリセットされました。(ConnectionReset)")
            except Exception as e:
                self.handle_disconnection(f"送信エラー: {e}")

    def handle_ai_positive_click(self):
        """AIポジティブボタンのクリック処理（トグル方式に変更）"""
        if self.ai_positive_button.cget('state') == 'disabled' or not self.is_connected:
            return
        
        # トグル動作
        if not self.ai_positive_active:
            self.ai_positive_active = True
            self.ai_positive_button.configure(text="ポジティブ", fg_color=("#4CAF50", "#388E3C"))
        else:
            self.ai_positive_active = False
            self.ai_positive_button.configure(text="ポジティブ", fg_color=("#808080", "#606060"))

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
                elif message.startswith("SYSTEM:"):
                    self.display_message(message, tag='system')
                elif message.startswith("(個人 from"): # (個人 from Sender): Message
                    self.display_message(message, tag='pm_received')
                elif message.startswith("(個人 to"):   # (個人 to Recipient): Message
                    self.display_message(message, tag='pm_sent')
                # elif message.startswith("GEMINI_RESPONSE:"): # Geminiからの応答 # 変更
                #     # プレフィックス "GEMINI_RESPONSE:" を除去して表示
                #     # サーバー側で "Gemini: " が付与されていることを想定
                #     actual_message = message.split(":", 1)[1].strip() if ":" in message else message.strip() 
                #     self.display_message(actual_message, tag='gemini_response_tag')
                elif message.startswith("AI_POSITIVE_RESPONSE:"): # AIポジティブ変換応答の処理
                    # 例: AI_POSITIVE_RESPONSE:OriginalUser (ポジティブ): Transformed Message
                    actual_message = message.split(":", 1)[1].strip() if ":" in message else message.strip()
                    self.display_message(actual_message, tag='ai_positive_response_tag')
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
            self.is_connected = False
            self.master.after(0, lambda: self.disconnect_from_server(show_info=True, reason=reason_message))

    def on_closing(self):
        if self.is_connected:
            self.disconnect_from_server(show_info=False)
        self.master.destroy()

    def show_help(self):
        """ヘルプメッセージを表示"""
        help_message = """🎉 チャット機能ガイド 🎉

📱 基本的なチャット機能:
• 普通にメッセージを入力すると、全員に送信されます
• Enterキーでも送信できます

🚀 特別なコマンド機能:
• /users - 現在接続中のユーザー一覧を表示
• /w ユーザー名 メッセージ - 特定のユーザーに個人メッセージを送信
• /msg ユーザー名 メッセージ - 個人メッセージの別コマンド

✨ 魔法のポジティブ機能 ✨
「ポジティブ」ボタンを押すと、あなたのメッセージが
AIによって自動的にポジティブで明るい表現に変換されます！

例:
「疲れた...」→「今日もお疲れ様でした！明日はきっと素晴らしい日になりますね🌟」
「難しい」→「挑戦しがいがありますね！一歩ずつ進んでいきましょう💪」

ポジティブモードを有効にすると、ボタンが緑色に光ります！
もう一度押すと通常モードに戻ります。

🎊 みんなで楽しくチャットしましょう！ 🎊"""
        
        messagebox.showinfo("チャット機能ヘルプ", help_message, parent=self.master)

if __name__ == '__main__':
    root = ctk.CTk()
    app = ChatClientGUI(root)
    root.mainloop()
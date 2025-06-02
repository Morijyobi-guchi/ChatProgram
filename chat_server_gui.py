import customtkinter as ctk
from tkinter import messagebox, PhotoImage
from tkinter.simpledialog import askstring
import socket
import threading
import datetime
import os
import google.generativeai as genai

class ChatServerGUI:
    def __init__(self, master):
        self.master = master
        master.title("チャットサーバー")
        master.geometry("550x400")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # アイコン設定 (オプション: .pngファイルを同じディレクトリに配置)
        try:
            icon = PhotoImage(file='server_icon.png')
            master.iconphoto(True, icon)
        except Exception:
            print("サーバーアイコンが見つかりません。スキップします。")

        self.log_label = ctk.CTkLabel(master, text="サーバーログ:")
        self.log_label.pack(pady=(10,0))

        self.log_area = ctk.CTkTextbox(master, state='disabled', wrap="word", height=250)
        self.log_area.pack(pady=5, padx=10, fill="both", expand=True)

        self.button_frame = ctk.CTkFrame(master, fg_color="transparent")
        self.button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(self.button_frame, text="サーバー起動", command=self.start_server_prompt)
        self.start_button.pack(side="left", padx=20)

        self.stop_button = ctk.CTkButton(self.button_frame, text="サーバー停止", command=self.stop_server, state='disabled')
        self.stop_button.pack(side="left", padx=20)

        self.server_socket = None
        self.client_sockets = []
        self.is_running = False
        self.listen_thread = None
        self.chat_history = []
        self.MAX_HISTORY_LINES = 50
        self.SUMMARY_LINES_FOR_GEMINI = 30
        self.MAX_HISTORY_LINES = 50
        self.port = 50000  # デフォルトポート追加

        # Gemini API設定
        self.gemini_api_key = os.getenv("API_Gemini")
        self.gemini_model = None
        self.gemini_enabled = False

        if not self.gemini_api_key:
            self.log_message("環境変数 API_Gemini が設定されていません。Gemini機能は無効です。", "WARN")
        else:
            try:
                genai.configure(api_key=self.gemini_api_key)
                # Gemini 2.0 Flashを最優先に、その後無料モデルをフォールバック
                try:
                    self.gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    model_name = 'models/gemini-1.5-flash-latest'
                except:
                    raise Exception("利用可能なGeminiモデルが見つかりません")
                
                self.gemini_enabled = True
                self.log_message(f"Gemini APIの準備ができました (model: {model_name})。", "INFO")
            except Exception as e:
                self.log_message(f"Gemini APIの初期化に失敗しました: {e}", "ERROR")
                self.gemini_enabled = False

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log_message(self, message, level="INFO"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{now}] [{level}] {message}\n"
        
        self.log_area.configure(state='normal')
        self.log_area.insert("end", formatted_message)
        self.log_area.see("end")
        self.log_area.configure(state='disabled')
        print(formatted_message.strip())

    def start_server_prompt(self):
        port_str = askstring("ポート番号", "サーバーを起動するポート番号を入力してください:", initialvalue=str(self.port), parent=self.master)
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
            self.start_button.configure(state='disabled')
            self.stop_button.configure(state='normal')

            self.listen_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.listen_thread.start()
        except Exception as e:
            self.log_message(f"サーバー起動エラー: {e}", "ERROR")
            messagebox.showerror("起動エラー", f"サーバー起動に失敗しました: {e}", parent=self.master)
            if self.server_socket:
                self.server_socket.close()
            self.is_running = False
            self.start_button.configure(state='normal')

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
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dummy_socket:
                    dummy_socket.settimeout(0.1)
                    dummy_socket.connect(("127.0.0.1", self.port))
            except:
                pass
            finally:
                self.server_socket.close()
                self.server_socket = None

        if self.listen_thread and self.listen_thread.is_alive():
             self.listen_thread.join(timeout=0.5)

        if show_log: self.log_message("サーバーが停止しました。")
        self.start_button.configure(state='normal')
        self.stop_button.configure(state='disabled')

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
                elif message_str.startswith("/ask_gemini "): 
                    if not self.gemini_enabled or not self.gemini_model:
                        self.send_to_client(client_socket, "SYSTEM: Geminiが現在利用できません。")
                        self.log_message(f"User {username} tried to ask Gemini, but it's not enabled/initialized.", "WARN")
                        continue
                    question = message_str.split(" ", 1)[1]
                    self.trigger_ask_gemini(client_socket, username, question)
                elif message_str.startswith("/positive_transform "): # 新しいコマンドの処理
                    if not self.gemini_enabled or not self.gemini_model:
                        self.send_to_client(client_socket, "SYSTEM: AI変換機能が現在利用できません。")
                        self.log_message(f"User {username} tried to use AI positive transform, but Gemini is not enabled/initialized.", "WARN")
                        continue
                    original_message = message_str.split(" ", 1)[1]
                    self.trigger_positive_transform(client_socket, username, original_message)
                elif message_str.strip().lower() == "/summarize_gemini":
                    self.trigger_gemini_summary(client_socket, username)
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
            self.log_message(f"特定クライアントへの送信エラー: {e}", "ERROR")

    def trigger_gemini_summary(self, client_socket, username):
        if not self.gemini_api_key or not self.gemini_model:
            self.send_to_client(client_socket, "SYSTEM_GEMINI_SUMMARY: Gemini APIが利用できないため、要約を生成できません。")
            self.log_message(f"ユーザー {username} のGemini要約リクエスト失敗: API未設定", "WARN")
            return

        if not self.chat_history:
            self.send_to_client(client_socket, "SYSTEM_GEMINI_SUMMARY: 要約対象のチャット履歴がありません。")
            self.log_message(f"ユーザー {username} のGemini要約リクエスト失敗: 履歴なし", "INFO")
            return

        self.send_to_client(client_socket, "SYSTEM_INFO: Gemini APIによる要約を生成中です。少々お待ちください...")
        self.log_message(f"ユーザー {username} からGemini要約リクエストを受信。処理を開始します。", "INFO")

        # API呼び出しを別スレッドで実行
        threading.Thread(target=self.execute_gemini_summary, args=(client_socket, username), daemon=True).start()


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
        # Geminiの応答も履歴に含める
        if message_string.startswith("GEMINI_RESPONSE:"):
            actual_gemini_message = message_string.split(":", 1)[1] if ":" in message_string else message_string
            self.chat_history.append(actual_gemini_message.strip())
            self.log_message(f"履歴追加 (Gemini): {actual_gemini_message.strip()}", "DEBUG")
        elif message_string.startswith("AI_POSITIVE_RESPONSE:"): # AIポジティブ応答の履歴追加
            actual_positive_message = message_string.split(":", 1)[1].strip() if ":" in message_string else message_string.strip()
            self.chat_history.append(actual_positive_message)
            self.log_message(f"履歴追加 (AI Positive): {actual_positive_message}", "DEBUG")
        elif sender_socket is not None and not message_string.startswith("SYSTEM:"):
            self.chat_history.append(message_string)
            if len(self.chat_history) > self.MAX_HISTORY_LINES:
                self.chat_history.pop(0)
        
        for client_info_b in self.client_sockets:
            client_sock_b, _, username_b = client_info_b
            if sender_socket is None or client_sock_b != sender_socket:
                try:
                    client_sock_b.sendall(message_string.encode('utf-8'))
                except Exception as e:
                    self.log_message(f"ブロードキャストエラー ({username_b}): {e}", "ERROR")

    def trigger_ask_gemini(self, client_socket, username, question):
        if not self.gemini_enabled or not self.gemini_model:
            self.send_to_client(client_socket, "SYSTEM: Gemini APIが現在利用できません。")
            self.log_message(f"ユーザー {username} のGemini質問リクエスト失敗: Gemini無効またはモデル未初期化", "WARN")
            return

        self.log_message(f"ユーザー {username} からGeminiへの質問「{question}」を受信。処理を開始します。", "INFO")

        # API呼び出しを別スレッドで実行
        threading.Thread(target=self.execute_ask_gemini_sync, args=(username, question), daemon=True).start()

    def trigger_positive_transform(self, client_socket, username, original_message):
        if not self.gemini_enabled or not self.gemini_model: # Gemini APIを流用
            self.send_to_client(client_socket, "SYSTEM: AI変換機能が現在利用できません。")
            self.log_message(f"ユーザー {username} のAIポジティブ変換リクエスト失敗: Gemini無効またはモデル未初期化", "WARN")
            return

        self.log_message(f"ユーザー {username} からAIポジティブ変換リクエスト「{original_message}」を受信。処理を開始します。", "INFO")
        # API呼び出しを別スレッドで実行
        threading.Thread(target=self.execute_positive_transform, args=(username, original_message), daemon=True).start()

    def execute_positive_transform(self, username, original_message):
        try:
            # チャット履歴を取得して文脈情報として使用
            history_snapshot = list(self.chat_history)
            context_history = "\n".join(history_snapshot[-10:]) if history_snapshot else "（履歴なし）"
            
            prompt = f"""あなたは、送信者{username}の発言を変換し、どんな悪口やネガティブな表現でも非常にポジティブな言い回しに変換するAIです。自然で簡潔な応答をしてください。
。絵文字は使用しないでください。

過去のチャット履歴（文脈参考用）:
{context_history}

変換対象のメッセージ送信者: {username}←ここを変更する
変換前のメッセージ:
「{original_message}」←ここを変更する【重要】

上記の履歴と文脈を踏まえて、変換後のメッセージだけを、チャットでそのまま送信できる形で出力してください。「」で囲む必要はありません。
ポジティブな表現にする上で表現方法は変わる可能性がありますが、元々のメッセージの内容は変えず表現方法を
変えるだけにしてください。例えば、悪口やネガティブな表現をポジティブな表現に変換することが求められます。
会話の流れに合わせて、より適切で自然なポジティブ表現にしてください。

例：
変換前：「うるさい」
変換後：「盛り上げてくれてありがとう」
"""
            
            self.log_message(f"GeminiにAIポジティブ変換を送信中 ({username}): {original_message[:30]}...", "DEBUG")
            response = self.gemini_model.generate_content(prompt)
            transformed_message_text = response.text.strip()
            
            response_for_broadcast = f"AI_POSITIVE_RESPONSE:{username} : {transformed_message_text}"
            self.master.after(0, self.broadcast_ai_response_message, response_for_broadcast)
            self.master.after(0, self.log_message, f"AIポジティブ変換の応答をブロードキャスト準備 ({username}のメッセージ「{original_message[:30]}...」に対して)", "INFO")

        except Exception as e:
            error_message = f"AIポジティブ変換 APIエラー (依頼者 {username}): {e}"
            self.master.after(0, self.log_message, error_message, "ERROR")
            # エラー発生を依頼者に通知する場合は、client_socketを渡すか、usernameから検索する処理が必要

    def broadcast_ai_response_message(self, message_text_with_prefix):
        """AIからのメッセージ(Gemini応答、ポジティブ変換応答など)をブロードキャストし、ログに記録する"""
        self.broadcast_message(message_text_with_prefix, None)

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
    root = ctk.CTk()
    app = ChatServerGUI(root)
    root.mainloop()
# オリジナルチャットプログラム
GUI環境によるTCPを利用したオリジナルChatプログラムを作成

## 必要なライブラリのインストール

### 基本ライブラリ
```bash
pip install -r requirements.txt
```

## Gemini API設定

1. Google AI Studioでプロジェクトを作成
2. API Keyを取得
3. 環境変数を設定：
   ```bash
   # Windows
   set API_Gemini=your_api_key_here
   
   # Linux/Mac
   export API_Gemini=your_api_key_here
   ```

### アプリケーションの起動

#### サーバーの起動
```bash
python chat_server_gui.py
```
1. 「サーバー起動」ボタンをクリック
2. ポート番号を入力（デフォルト: 50000）
3. サーバーが起動したことを確認

#### クライアントの起動
```bash
python chat_client_gui.py
```
1. サーバーIP、ポート、ユーザー名を入力
2. 「接続」ボタンをクリック
3. チャットを開始


## 機能

- 複数クライアント同時接続
- 個人メッセージ機能 (/w ユーザー名 メッセージ)
- ユーザーリスト表示 (/users)
- ポジティブなメッセージをGemini APIで生成

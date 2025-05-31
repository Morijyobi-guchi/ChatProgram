# チャットプログラム
GUI環境によるTCPを利用したオリジナルChatプログラムを作成

## 必要なライブラリのインストール

### 基本ライブラリ
```bash
pip install google-generativeai
```

または、requirements.txtを使用：
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

## 実行方法

### サーバー起動
```bash
python chat_server_gui.py
```

### クライアント起動
```bash
python chat_client_gui.py
```

## 機能

- 複数クライアント同時接続
- 個人メッセージ機能 (/w ユーザー名 メッセージ)
- ユーザーリスト表示 (/users)
- Gemini AI による会話要約 (/summarize_gemini)

import os
try:
    import google.generativeai as genai
    
    api_key = os.getenv("API_Gemini")
    if not api_key:
        print("環境変数 API_Gemini が設定されていません。")
        exit(1)
    
    genai.configure(api_key=api_key)
    
    print("利用可能なGeminiモデル:")
    print("-" * 50)
    
    models = genai.list_models()
    for model in models:
        print(f"モデル名: {model.name}")
        print(f"表示名: {model.display_name}")
        print(f"サポートされている機能: {model.supported_generation_methods}")
        print(f"入力トークン制限: {model.input_token_limit}")
        print(f"出力トークン制限: {model.output_token_limit}")
        print("-" * 30)
        
    # generateContentをサポートするモデルのみ抽出
    compatible_models = [m for m in models if 'generateContent' in m.supported_generation_methods]
    
    print("\nチャットアプリで使用可能なモデル:")
    for model in compatible_models:
        model_id = model.name.split('/')[-1]
        print(f"- {model_id} ({model.display_name})")
        
except ImportError:
    print("google-generativeai ライブラリがインストールされていません。")
    print("インストールコマンド: pip install google-generativeai")
except Exception as e:
    print(f"エラーが発生しました: {e}")

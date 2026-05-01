"""
AIブリッジ株式会社 HP 用チャットボット バックエンド
Flask + Anthropic SDK (ストリーミング対応)
"""

import os
import json
import pathlib
from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS
import anthropic

app = Flask(__name__)
CORS(app)  # ローカル開発用に全オリジンを許可

# ── API キーの取得 ──────────────────────────────────────────
# 優先順位:
#   1. 環境変数 ANTHROPIC_API_KEY
#   2. ~/.claude/settings.json の env.ANTHROPIC_API_KEY
def _load_api_key() -> str:
    # 1. 環境変数
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key

    # 2. Claude Code の設定ファイル
    settings_path = pathlib.Path.home() / ".claude" / "settings.json"
    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("env", {}).get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:
        pass

    return ""

_api_key = _load_api_key()
client = anthropic.Anthropic(api_key=_api_key if _api_key else None)

# チャットボットのシステムプロンプト
SYSTEM_PROMPT = """あなたは「AIブリッジ株式会社」のWebサイトに設置されたAIアシスタントです。

【会社情報】
- 会社名: AIブリッジ株式会社
- 設立: 2020年4月
- 所在地: 東京都渋谷区
- 事業内容: AI業務効率化支援・DXコンサルティング・データ活用支援
- 強み: 低コスト・最短2週間での導入対応、中小企業向けプラン
- キャッチコピー: 「AIで、もっと速く。もっと安く。」

【サービス名】
AIの自動化、AIコンサル

【サービス内容と料金】
- GAS（Google Apps Script自動化）: 5,000円
- チャットボット制作: 50,000円
- AIコンサル: 100,000円

【導入実績】
- 株式会社サンプル商事（小売業）: AI在庫管理ツール導入で業務工数40%削減を実現

【営業時間・連絡先】
- TEL: 0123456789
- メールアドレス: mmm@mmmm

【よくある質問と回答】
Q: AIのことがまったくわからないのですが大丈夫ですか？
A: もちろん大丈夫です！まずはお気軽にご相談ください。わかりやすく丁寧にご説明いたします。

Q: 自社に来てもらうことはできますか？
A: はい、訪問対応も可能です。お気軽にご連絡ください。

【対応方針】
- 丁寧かつ親しみやすいトーンで回答する
- 料金を聞かれたら上記の料金を具体的に案内する
- 連絡先を聞かれたらTELとメールアドレスを案内する
- よくある質問に近い内容はFAQの回答をベースに答える
- 無料相談への誘導はページ下部の「お問い合わせ」フォームも案内する
- 会社に関係のない話題は「申し訳ございませんが、AIブリッジに関するご質問にお答えしております」と丁寧に断る
- 回答は簡潔にまとめ、長くなりすぎないようにする
"""


@app.route("/chat", methods=["POST"])
def chat():
    """
    チャットエンドポイント（Server-Sent Events でストリーミング返却）
    リクエスト JSON: {"messages": [{"role": "user"/"assistant", "content": "..."}]}
    """
    data = request.get_json()
    if not data or "messages" not in data:
        return {"error": "messages フィールドが必要です"}, 400

    messages = data["messages"]

    def generate():
        try:
            # ストリーミングで Claude API を呼び出す
            with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
                thinking={"type": "adaptive"},
            ) as stream:
                for text in stream.text_stream:
                    # SSE 形式で送信
                    yield f"data: {json.dumps({'text': text})}\n\n"

            # ストリーム終了を通知
            yield "data: [DONE]\n\n"

        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'error': 'APIキーが無効です。ANTHROPIC_API_KEY を確認してください。'})}\n\n"
        except anthropic.RateLimitError:
            yield f"data: {json.dumps({'error': 'リクエスト制限に達しました。しばらくお待ちください。'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'エラーが発生しました: {str(e)}'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/health", methods=["GET"])
def health():
    """動作確認用エンドポイント"""
    return {"status": "ok", "message": "AIブリッジ チャットボット サーバー稼働中"}


if __name__ == "__main__":
    import sys
    # Windows でも絵文字を表示できるよう UTF-8 に設定
    sys.stdout.reconfigure(encoding="utf-8")

    # ANTHROPIC_API_KEY が設定されているか確認
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[警告] 環境変数 ANTHROPIC_API_KEY が設定されていません。")
        print("       Claude Code の設定ファイル (~/.claude/settings.json) を確認してください。")
    else:
        print("[OK] ANTHROPIC_API_KEY が設定されています。")

    print("[起動] サーバーを起動します: http://localhost:5000")
    app.run(debug=True, port=5000)

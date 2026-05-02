"""
Vercel サーバーレス関数 — Claude API チャットエンドポイント
/api/chat に POST リクエストを受け付け、JSON で返す
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import anthropic

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


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        """CORS プリフライトリクエストへの対応"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        """チャットリクエストを受け取り Claude API を呼び出す"""
        try:
            # リクエストボディを読み取る
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            messages = data.get('messages', [])

            # Claude API を呼び出す
            client = anthropic.Anthropic(
                api_key=os.environ.get('ANTHROPIC_API_KEY', '')
            )
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )

            bot_text = response.content[0].text

            # 成功レスポンス
            self.send_response(200)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'text': bot_text}).encode('utf-8'))

        except anthropic.AuthenticationError:
            self._error(401, 'APIキーが無効です。')
        except anthropic.RateLimitError:
            self._error(429, 'リクエスト制限に達しました。しばらくお待ちください。')
        except Exception as e:
            self._error(500, f'エラーが発生しました: {str(e)}')

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _error(self, code, message):
        self.send_response(code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Vercel のログに不要な出力を抑制

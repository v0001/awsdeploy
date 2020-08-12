# 1. 모듈가져오기
from flask import Flask, render_template, request

# 2. 앱 생성
app = Flask(__name__)

# 3. 라우팅
@app.route('/')
def home():
    return render_template('home.html')

# 4. 서버가동
if __name__ == '__main__':
    app.run(debug=True)
# 언어,감지 서비스의 엔트리 포인트(시작점,시작모듈)

# 1. 모듈가져오기
from flask import Flask, render_template, request,jsonify
from service import loadMLModel,langDetect
from db import *

# 2. 앱 생성
app = Flask(__name__)


#3. 라우팅
@app.route('/')
def home():
    return render_template('home.html')

#4. 서버 가동

if __name__ == '__main__':
    _,l = loadMLModel()
    print(l)
    app.run(debug=True)
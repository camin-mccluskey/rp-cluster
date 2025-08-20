from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    with open('/data/temp.text', 'w+') as f:
        var = int(f.read())
        var += 1
        f.write(str(var))
        return var

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

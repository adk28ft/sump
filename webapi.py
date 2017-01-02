from flask import Flask
import thread

data = 'foo-bar'
app = Flask(__name__)

@app.route("/")
def mainRoute():
    return data

def startFlaskThread():
    app.run(debug=True)

if __name__ == "__main__":
#    thread.start_new_thread(startFlaskThread,())
    startFlaskThread()


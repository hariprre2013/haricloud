# /usr/bin/env python3
import json
import logging
import math
import os
import random
import yfinance as yf
import pandas as pd
from flask import Flask, render_template, request, jsonify
from datetime import date, timedelta
from pandas_datareader import data as pdr

app = Flask(__name__)


@app.route('/')
@app.route('/home.html')
def home():
    return render_template('home.html')


def doRender(tname, values={}):  # from labs
    if not os.path.isfile(os.path.join(os.getcwd(), 'templates/' + tname)):  # No such file
        return render_template('home.html')
    return render_template(tname, **values)



# override yfinance with pandas – seems to be a common step
yf.pdr_override()
# Get stock data from Yahoo Finance – here, asking for about 10 years of Gamestop
# which had an interesting time in 2021: https://en.wikipedia.org/wiki/GameStop_short_squeeze
today = date.today()
decadeAgo = today - timedelta(days=3652)
dat = today.strftime("%m/%d/%Y")
data = pdr.get_data_yahoo('GME', start=decadeAgo, end=today)
# Other symbols: TSLA – Tesla, AMZN – Amazon, NFLX – Netflix, BP.L – BP
# Add two columns to this to allow for Buy and Sell signals
# fill with zero
data['Buy'] = 0
data['Sell'] = 0
# Find the 4 different types of signals – uncomment print statements
# if you want to look at the data these pick out in some another way
for i in range(len(data)):
    # Hammer
    realbody = math.fabs(data.Open[i] - data.Close[i])
    bodyprojection = 0.3 * math.fabs(data.Close[i] - data.Open[i])
    if data.High[i] >= data.Close[i] and data.High[i] - bodyprojection <= data.Close[i] and data.Close[i] > data.Open[i] \
            and data.Open[i] > data.Low[i] and data.Open[i] - data.Low[i] > realbody:
        data.at[data.index[i], 'Buy'] = 1
        # print("H", data.Open[i], data.High[i], data.Low[i], data.Close[i])
        # Inverted Hammer
    if data.High[i] > data.Close[i] and data.High[i] - data.Close[i] > realbody and data.Close[i] > data.Open[i] and \
            data.Open[i] >= data.Low[i] and data.Open[i] <= data.Low[i] + bodyprojection:
        data.at[data.index[i], 'Buy'] = 1
        # print("I", data.Open[i], data.High[i], data.Low[i], data.Close[i])
        # Hanging Man
    if data.High[i] >= data.Open[i] and data.High[i] - bodyprojection <= data.Open[i] and data.Open[i] > data.Close[
        i] and data.Close[i] > data.Low[i] and data.Close[i] - data.Low[i] > realbody:
        data.at[data.index[i], 'Sell'] = 1
    # print("M", data.Open[i], data.High[i], data.Low[i], data.Close[i])
    # Shooting Star
    if data.High[i] > data.Open[i] and data.High[i] - data.Open[i] > realbody and data.Open[i] > data.Close[i] and \
            data.Close[i] >= data.Low[i] and data.Close[i] <= data.Low[i] + bodyprojection:
        data.at[data.index[i], 'Sell'] = 1
    # print("S", data.Open[i], data.High[i], data.Low[i], data.Close[i])
    # Now have signals, so if they have the minimum amount of historic data can generate
    # the number of simulated values (shots) needed in line with the mean and standard
    # deviation of the that recent history


minhistory = 101
shots = 80000
list95 = []
list99 = []
dt = []
mh = []
sh = []
d = [dat]


@app.route("/", methods=['POST', 'GET'])
def risk():
    if request.method == "POST":
        m = request.form['m']
        s = request.form['s']
        bs = request.form['bs']
        m = int(m)
        s = int(s)
        print(s)
        bs = int(bs)
        mh.clear()
        mh.append(m)
        sh.clear()
        sh.append(s)
        list95.clear()
        list99.clear()
        if bs == 1:
            for i in range(m, len(data)):
                if data.Buy[i] == 1:  # if we were only interested in Buy signals
                    mean = data.Close[i - m:i].pct_change(1).mean()
                    std = data.Close[i - m:i].pct_change(1).std()
                    # generate rather larger (simulated) series with same broad characteristics
                    simulated = [random.gauss(mean, std) for x in range(s)]
                    # sort, and pick 95% and 99% losses (not distinguishing any trading position)
                    simulated.sort(reverse=True)
                    var95 = simulated[int(len(simulated) * 0.95)]
                    list95.append(var95)
                    var99 = simulated[int(len(simulated) * 0.99)]
                    list99.append(var99)
                    print(var95, var99)  # so you can see what is being produced

                    def re():
                        v1 = var95
                        v2 = var99
                        return [v1, v2]

                    re = re()
                    st = json.dumps(re)
        else:
            for i in range(m, len(data)):
                if data.Sell[i] == 1:  # if we were only interested in Buy signals
                    mean = data.Close[i - m:i].pct_change(1).mean()
                    std = data.Close[i - m:i].pct_change(1).std()
                    # generate rather larger (simulated) series with same broad characteristics
                    simulated = [random.gauss(mean, std) for x in range(s)]
                    # sort, and pick 95% and 99% losses (not distinguishing any trading position)
                    simulated.sort(reverse=True)
                    var95 = simulated[int(len(simulated) * 0.95)]
                    list95.append(var95)
                    var99 = simulated[int(len(simulated) * 0.99)]
                    list99.append(var99)
                    print(var95, var99)  # so you can see what is being produced

                    def re():
                        v1 = var95
                        v2 = var99
                        return [v1, v2]

                    re = re()
                    st = json.dumps(re)
        dt.clear()
        dt.extend([d] * len(list95))
        print(len(dt), len(list99), len(list95), mh, sh)
        return render_template('chart.html', date=dt, val95=list95, val99=list99, rv_95=list95[-1], rv_99=list99[-1],
                               mh=mh,
                               sh=sh)
    else:
        st = json.dumps(list95)
        return render_template('home.html', jsonify(st))


@app.errorhandler(500)
# A small bit of error handling
def server_error(e):
    logging.exception('ERROR!')
    return """An error occurred: <pre>{}</pre>""".format(e), 500


if __name__ == "__main__":
    app.run(port=8080, debug=True)

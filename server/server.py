import os
from flask import Flask, request, jsonify
from flask.ext.cors import CORS, cross_origin
import json
import components
import compiler
import pbl
import time

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.route('/inventory')
@cross_origin()
def inventory():
    start = time.time()
    print 'inventory'
    results = {
        'status': 'ok',
        'inventory': components.exported_inventory
    }
    print 'inventory', time.time() - start
    return jsonify(results)

@app.route('/run', methods=['GET', 'POST'])
@cross_origin()
def run():
    print 'inventory'
    start = time.time()
    program = request.json
    print 'got program', program
    status, obj = compiler.compile(program)

    print 'compiled in', time.time() - start, 'secs'

    if 'max_tracks' in program:
        max_tracks = program['max_tracks']
    else:
        max_tracks = 40

    results = { 'status': status}

    if status == 'ok':
        tracks = []
        tids = pbl.get_tracks(obj, max_tracks)
        print
        for i, tid in enumerate(tids):
            print i, pbl.tlib.get_tn(tid)
            tracks.append(pbl.tlib.get_track(tid))
        print
        results['tracks'] = tracks
        results['name'] = obj.name

    results['time'] = time.time() - start
    print 'compiled and executed in', time.time() - start, 'secs'
    if app.trace:
        print json.dumps(results, indent=4)
    print 'run', time.time() - start
    return jsonify(results)
  
#@app.errorhandler(Exception)
def handle_invalid_usage(error):
    start = time.time()
    print error
    results = { 'status': 'exception: '  + str(error)}
    print 'invalid usage', time.time() - start
    return jsonify(results)

if __name__ == '__main__':
    if os.environ.get('PBL_NO_CACHE'):
        app.debug = True
        app.trace = True
        print 'debug  mode'
    else:
        app.trace = False
        print 'prod  mode'
    app.run()
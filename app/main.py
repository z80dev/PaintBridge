#!/usr/bin/env python3

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/endpoint1', methods=['GET'])
def endpoint1():
    return jsonify({"message": "This is endpoint 1"})

@app.route('/api/endpoint2', methods=['GET'])
def endpoint2():
    return jsonify({"message": "This is endpoint 2"})


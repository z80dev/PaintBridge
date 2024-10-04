#!/usr/bin/env python3

from flask import Flask, jsonify

from .nft import get_bridged_address

app = Flask(__name__)

@app.route('/api/endpoint1', methods=['GET'])
def endpoint1():
    return jsonify({"message": "This is endpoint 1"})

@app.route('/api/endpoint2', methods=['GET'])
def endpoint2():
    return jsonify({"message": "This is endpoint 2"})

# endpoint that takes a parameter
@app.route('/api/endpoint3/<param>', methods=['GET'])
def endpoint3(param):
    bridged_address = get_bridged_address(param)
    return jsonify({"message": f"This is endpoint 3 with parameter {param} and bridged address {bridged_address}"})

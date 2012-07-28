var server = require('./server.js')
  , utils = require('./utils.js')
  , ioendpoint = require('./ioendpoint.js');

// Express and socket.io based server
function WebSocketServer(name, endpoints, port) {
	// defaults
	endpoints = endpoints || [];
	
	// private
	var express = require('express')
	  , app = express.createServer()
	  , connect_ep = ioendpoint.IOConnectionEndpoint(app)
	  , client_eps = {}
	  , client_callback = null;
	
	function _start_main_server() {
		console.log
		app.listen(port);
		socket_server.Super.start_main_server();
	}
	
	function _activate_endpoints() {
		connect_ep.onconnect(_on_connect);
		socket_server.Super.activate_endpoints();
	}
	
	function _on_connect(socket) {
		var client = ioendpoint.IOClientServiceEndpoint(socket);
		client.activate();
		client_eps[socket.id] = client;
		if (client_callback) client_callback(client);
	}
	
	function _new_client_callback(callback) {
		client_callback = callback;
	}
	
	// public
	var socket_server = {
		activate_endpoints: _activate_endpoints,
		start_main_server: _start_main_server,
		get connection_endpoint() { return connect_ep; },
		get clients() { return client_eps; },
		onclient: _new_client_callback
	}
	
	// inheritance
	utils.inherit(socket_server, server.Server, [name, endpoints]);
	
	// Add default IO Endpoint
	socket_server.add_endpoint(connect_ep);
	
	return socket_server;
}

// Exports

var exports = {};
exports.WebSocketServer = WebSocketServer;

module.exports = exports;

var server = require('./server.js')
  , utils = require('./utils.js')
  , ioendpoint = require('./ioendpoint.js');


// Express based server
function ExpressServer(name, endpoints, port) {
	// private
	var express = require('express')
	  , app = express.createServer()
	  ;
	  
	function _start_main_server() {
		express_server.Super.start_main_server();
		app.listen(port);
	}
	
	function _get(route, fn) {
		app.get(route, fn);
	}
	
	// public
	var express_server = {
		start_main_server: _start_main_server,
		get context() { return app; },
		get get() { return _get; }
	}
	
	utils.inherit(express_server, server.Server, [name, endpoints]);
	
	return express_server;
}

// Express and socket.io based server
function WebSocketServer(name, endpoints, port) {
	// defaults
	endpoints = endpoints || [];
	
	// private
	var client_eps = {}
	  , rooms = {}
	  , client_callback = null;
	
	function _start_main_server() {
		// This order is important
		socket_server.self.add_endpoint(connect_ep);
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
	
	function _create_room(name) {
		if (!rooms[name]) rooms[name] = ioendpoint.IORoomEndpoint(connect_ep.socketio, name);
		return rooms[name];
	}
	
	// public
	var socket_server = {
		activate_endpoints: _activate_endpoints,
		start_main_server: _start_main_server,
		get connection_endpoint() { return connect_ep; },
		get clients() { return client_eps; },
		get rooms() { return rooms; },
		get room() { return _create_room; },
		onclient: _new_client_callback
	}
	
	// inheritance
	utils.inherit(socket_server, ExpressServer, [name, endpoints, port]);
	
	// Add default IO Endpoint
	// We cannot rely on Super for this, since at that time we dont have the 'server' running
	var connect_ep = ioendpoint.IOConnectionEndpoint(socket_server.context);
	
	return socket_server;
}

// Exports

var exports = {};
exports.WebSocketServer = WebSocketServer;

module.exports = exports;

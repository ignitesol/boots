var utils = require('./utils.js')
  , ep = require('./endpoint.js');

function IOConnectionEndpoint(_context, _onconnect) {
	// private
	var connection_callback = _onconnect
	  , context = _context
	  , iolib = require('socket.io')
	  , io = null;
	 
	 function _activate() {
	 	io = iolib.listen(context);
	 	io.set('log level', 2);
	 	io.sockets.on('connection', connection_callback);
	 }
	
	// public
	var io_conn = {
		activate: _activate,
		onconnect: function(callback) {
			connection_callback = callback;
			io && io.sockets.on('connection', connection_callback);
		}
	};
	
	// inheritance
	utils.inherit(io_conn, ep.EndPoint);
	
	return io_conn;
}

// socket.io based endpoint
function IOClientServiceEndpoint(_socket/*optional*/) {
	// private
	var socket = _socket || null;
	var _route_callbacks = {};
	
	function _activate(_socket/*optional*/) {
		io_ep.Super.activate();
		socket = _socket || socket; // optional, remain the same if nothing given
		utils.foreach(_route_callbacks, function(k, v) {
			socket.on(k, v);
		});
	}
	
	function _add_route_callback(route, callback) {
		_route_callbacks[route] = callback;
		if (socket) socket.on(route, callback);
	}
	
	function _remove_route(route, del_callback) {
		del_callback = del_callback || function(){ };
		delete _route_callbacks[route];
		if (socket) socket.removeListener(route, del_callback);
	}
	
	function _close() {
		if (socket) socket.close();
	}
	
	function _emit() {
		socket.emit.apply(socket, utils.listify_arguments(arguments));
	}
	
	function _join(room_name) {
		socket.join(room_name);
	}
	
	function _leave(room_name) {
		socket.leave(room_name);
	}
	
	// public
	var io_ep = {
		activate: _activate,
		close: _close,
		on: _add_route_callback,
		drop: _remove_route,
		get id() { return socket? socket.id: null; },
		get emit() { return _emit; },
		get join() { return _join; },
		get leave() { return _leave; }
	};
	
	// inheritance
	utils.inherit(io_ep, ep.EndPoint);
	return io_ep;
}

function IORoomEndpoint(_io, _name) {
	// private
	var io = _io
	  , name = _name
	  ;
	
	function _add_client(ep) {
		ep.join(name);
	}
	
	function _remove_client(ep) {
		ep.leave(name);
	}
	
	// public
	var room = {
		get name() { return name; },
		get include() { return _add_client; },
		get exclude() { return _remove_client; },
		get broadcast() { return io.sockets.in(name).emit; }
	}
	
	// inheritance
	utils.inherit(room, ep.EndPoint);
}

// Module Exports
var Exports = {};
Exports.IOConnectionEndpoint = IOConnectionEndpoint;
Exports.IOClientServiceEndpoint = IOClientServiceEndpoint;
Exports.IORoomEndpoint = IORoomEndpoint
module.exports = Exports;

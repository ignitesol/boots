var utils = require('./utils.js')
  , ep = require('./endpoint.js');

function IOConnectionEndpoint(_context, _onconnect) {
	// private
	var connection_callback = _onconnect
	  , context = _context
	  , iolib = require('socket.io')
	  , io = null;
	 
	 function _activate(server) {
	 	io = iolib.listen(context);
	 	io.set('log level', 2);
	 	io.sockets.on('connection', connection_callback);
	 	io_conn.Super.activate(server);
	 }
	
	// public
	var io_conn = {
		activate: _activate,
		onconnect: function(callback) {
			connection_callback = callback;
			io && io.sockets.on('connection', connection_callback);
		},
		get socketio() { return io; }
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
	
	function _activate(server, _socket/*optional*/) {
		io_ep.Super.activate(server);
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
		if (socket) {
			socket.removeAllListeners();
			socket.disconnect();
		}
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
	
	function _ondisconnect(fn) {
		socket.on('disconnect', function(){ fn(io_ep); });
	}
	
	function _socket_set() {
		var args = utils.listify_arguments(arguments);
		socket.set.apply(socket, args);
	}
	
	function _socket_get() {
		var args = utils.listify_arguments(arguments);
		socket.get.apply(socket, args);
	}
	
	// public
	var io_ep = {
		activate: _activate
	  , close: _close
	  , on: _add_route_callback
	  , drop: _remove_route
	  , ondisconnect: _ondisconnect
	  , get id() { return socket? socket.id: null; }
	  , get emit() { return _emit; }
	  , get join() { return _join; }
	  , get leave() { return _leave; }
	  , get disconnected() { return socket.diconnected; }
	  , get namespace() { return socket.namespace.name; }
	  , get store() { return _socket_set }
	  , get retrieve() { return _socket_get }
	};
	
	// inheritance
	utils.inherit(io_ep, ep.EndPoint);
	return io_ep;
}

/**
 * Rooms are managed by Socket IO internally
 * This is simply a wrapped method of getting these grouped sockets
 * It doesn't expose the sockets directly, 
 * but tries to get the Client endpoints for those sockets from its server
 * It does not support namespaces, only the default '/' namespace
 */
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
	
	function _broadcast() {
		var args = utils.listify_arguments(arguments)
		  , these_sockets = io.sockets.in(name)
		  ;
		
		these_sockets.emit.apply(these_sockets, args);
	}
	
	function _clients() {
		var clients = [];
		// Namespace adjusted room, currently we only use '/', i.e. no namespace
		var nsp_room = io.rooms['/' + name];
		// Get all socket ids of this room from the socketio manager
		if (nsp_room)
		{
			nsp_room.forEach(function(v, k) {
				clients.push(room.server.clients[v])
			});
		}
		return clients;
	}
	
	// public
	var room = {
		get name() { return name; }
	  , get include() { return _add_client; }
 	  , get exclude() { return _remove_client; }
	  , get broadcast() { return _broadcast; }
	  , get clients() { return _clients(); }
		
	}
	
	// inheritance
	utils.inherit(room, ep.EndPoint);
	
	return room;
}

// Module Exports
var Exports = {};
Exports.IOConnectionEndpoint = IOConnectionEndpoint;
Exports.IOClientServiceEndpoint = IOClientServiceEndpoint;
Exports.IORoomEndpoint = IORoomEndpoint
module.exports = Exports;

var utils = require('./utils.js')
  , zmq = require('zmq');

function EndPoint() {
	// private
	var _activated = false;
	var _uuid = utils.generate_UUID()

	function _activate() {
		_activated = true;
	}

	function _close() {
		_activated = false;
	}

	//public
	var endpoint = {
		activate : _activate,
		get activated() { return _activated; },
		close : _close,
		get uuid() { return _uuid; }
	};

	return endpoint;
}

function ZMQEndpoint(socket_type, address, bind, plugins, filters) {
	bind = bind || false;
	plugins = plugins || [];
	filters = filters || [];

	// private
	var _socket = null;
	var _filters = filters;
	var _plugins = plugins;
	var _bind = bind;
	var _address = address;
	var _socket_type = socket_type;

	var _recv_plugins = _plugins.filter(function(p) {
		return p.plugin_type === 'receive';
	});
	var _send_plugins = _plugins.filter(function(p) {
		return p.plugin_type === 'send';
	});
	function _activate() {
		zmq_endpoint.Super.activate();
		_setup();
		_start();
	}

	function _setup() {
		_socket = zmq.socket(zmq_endpoint.socket_type);
		_plugins.forEach(function(v) {
			v.setup(zmq_endpoint);
		});
	}

	function _start() {
		if(zmq_endpoint.bind)
			_socket.bind(zmq_endpoint.address);
		else
			_socket.connect(zmq_endpoint.address);
			
		if (socket_type === 'sub') _filters.forEach(function(v){ _socket.subscribe(v); })
		
		_socket.on('message', _recv_message);
	}

	function _send() {
		var msg = arguments;
		_send_plugins.forEach(function(v) {
			msg = v.apply(msg);
		});
		_socket.send(msg);
	}

	function _recv_message() {		
		var msg = utils.listify_arguments(arguments);
		msg.forEach( function(v, i) { msg[i] = v.toString(); } );
		
		// Plugins
		_recv_plugins.forEach(function(v) {
			msg = v.apply(msg);
		})
		// overridden callback
		zmq_endpoint.self.callback(msg);
	}

	function _callback(msg) {
		console.log(msg);
	}

	function _add_filter(filter) {
		if(zmq_endpoint.socket_type === 'sub') {
			if (zmq_endpoint.activated) {
				_socket.subscribe(filter);
			}
		} else
			throw Error('Socket must be of sub type')
			
		if (_filters.indexOf(filter) === -1) _filters.push(filter);
	}

	function _remove_filter(filter) {
		if(zmq_endpoint.socket_type === 'sub') {
			_socket.unsubscribe(filter);
			var tail = _filters.slice(_filters.indexOf(filter) + 1);
			_filters.splice(_filters.indexOf(filter));
			_filters = _filters.concat(tail);
		} else
			throw Error('Socket must be of sub type')
	}

	function _close() {
		zmq_endpoint.Super.close();
		_socket.close();
	}
	
	function _set_message_callback(fn) {
		_callback = fn;
	}

	// public
	var zmq_endpoint = {
		socket_type : _socket_type,
		address : _address,
		bind : _bind,
		activate : _activate,
		add_filter : _add_filter,
		remove_filter : _remove_filter,
		send : _send,
		onmessage: _set_message_callback,
		get callback() { return _callback; },
		close : _close
	};

	// inheritance
	utils.inherit(zmq_endpoint, EndPoint);

	return zmq_endpoint;
}

// Exports
Endpoints = {};
Endpoints.EndPoint = EndPoint;
Endpoints.ZMQEndpoint = ZMQEndpoint;

module.exports = Endpoints;
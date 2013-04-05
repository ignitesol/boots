// Some common utility functions
var utils = {
	/**
	 * foreach loop for objects
	 * removes the worrying about prototypes creeping into the loop
	 * calls back each_func with (key, value) arguments
	 */
	foreach: function(obj, each_func) {
	    for (var o in obj) if (obj.hasOwnProperty(o)) each_func(o, obj[o]);
	},
	
	/**
	 * In node the inbuilt arguments structure is a hash, not a list
	 * This handy function will listify the arguments in the order that
	 * that they were sent since the keys are numbered
	 */
	listify_arguments: function(args) {
		var l = []
		for(var i = 0; args[i] !== undefined; i++) {
			l.push(args[i].toString());
        }
		return l;
	},
	
	generate_UUID: function(frames) {
		frames = frames || 3;
		var uuid = [];
		for(var i = 0; i < frames; i ++) uuid.push((Math.random()*10000000 + 10000).toString(16).split('.')[0]);
		return uuid.join('-');
	},
	
	inherit: function(self, parent, args) {
		parent = (parent instanceof Array)? parent : [parent];
		args = (args instanceof Array)? args : [args];
		
		// Multiple inheritance, list of parents
		self._supers = [];
		parent.forEach(function(v, k) {
			self._supers.push(v.apply(v, args));
		});
		
		// MRO Chain starting points
		self.Super = {};
		function reorder_mro_chain(attr) {
			var supers = self._supers;
			var new_supers = [];
			var last_super = self;
			
			while(supers.length > 0) {
				supers.forEach(function(v, k) {
					if (v[attr]) {
						last_super.Super[attr] = v[attr];
						last_super = v;
					}
					if (v._supers) new_supers = new_supers.concat(v._supers); 
				});
				supers = new_supers;
				new_supers = [];
			}
		}
		
		
		// Multiple Inheritance MRO Chain
		// First containing parent gets priority
		var ii = self._supers.length;
		for (var i = 0; i < ii; i++) {
			for(var k in self._supers[i]) {
				reorder_mro_chain(k);
			}
		}
		
		/**
		 * In case of a Getter/Setter the Getting/Setting function will be executed
		 * only at runtime, and the index values i, k will be within a closured loop
		 * causing them to always have their maximum values
		 * This function will create a new closure that will keep the index values
		 * in the desired state
		 */
		function _augmenter_closure(i, k) {
			self.__defineGetter__(k, function(){ return self._supers[i][k]; });
			self.__defineSetter__(k, function(val){ self._supers[i][k] = val; });
		}
		
		// We want prototypes and key, values
		// First mentioned parent gets priority
		var ii = self._supers.length;
		for (var i = 0; i < ii; i++) {
			for(var k in self._supers[i]) {
				if (!self[k]) { 
					_augmenter_closure(i, k);
				}
			}
		}
		
		//reverse inheritance
		self.__defineSetter__('self', function(v) {
			this._self = v;
			this._supers.forEach(function(s) {
				s.self = v;
			});
		});
		
		self.__defineGetter__('self', function(){
			return this._self;
		});
		
		// Masochist
		self.self = self;
	}
}

// Exports
module.exports = utils;
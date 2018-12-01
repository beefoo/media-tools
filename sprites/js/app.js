'use strict';

var App = (function() {

  function App(config) {
    var defaults = {
      "uid": "ia_politicaladarchive"
    };

    this.opt = _.extend({}, defaults, config);
    this.init();
  }

  function lerp(a, b, percent) {
    return (1.0*b - a) * percent + a;
  }

  function norm(value, a, b){
    var denom = (b - a);
    if (denom > 0 || denom < 0) return (1.0 * value - a) / denom;
    else return 0;
  }

  App.prototype.init = function(){
    var _this = this;

    this.currentCell = "";

    var dataPromise = this.loadData();
    $.when(dataPromise).done(function(results){
      var audioPromise = _this.loadAudio(results);
      _this.loadUI(results);
      $.when(audioPromise).done(function(){
        _this.onReady();
      });
    });
  };

  App.prototype.loadAudio = function(options){
    var deferred = $.Deferred();

    var uid = this.opt.uid;
    var sounds = [];
    var spritePromises = [];
    var cols = options.cols;

    var allSprites = _.map(options.sprites, function(s, i){
      var row = Math.floor(i / cols);
      var col = i % cols;
      var id = row + "-" + col;
      return {
        "id": id,
        "fileIndex": s[0],
        "position": s.slice(1)
      }
    });
    this.spriteLookup = _.object(_.map(allSprites, function(s){ return [s.id, s.fileIndex]; }));

    _.each(options.audioSpriteFiles, function(fn, i){
      var audioFilename = uid + "/" + fn;
      var sprites = _.filter(allSprites, function(s){ return s.fileIndex===i; });
      sprites = _.map(sprites, function(s, i){ return [s.id, s.position]; });
      sprites = _.object(sprites);
      var promise = $.Deferred();
      var sound = new Howl({
        src: [audioFilename],
        sprite: sprites,
        onload: function(){
          console.log("Loaded "+audioFilename);
          promise.resolve();
        }
      });
      spritePromises.push(promise);
      sounds.push(sound);
    });

    this.sounds = sounds;

    $.when.apply(null, spritePromises).done(function() {
      deferred.resolve();
    });

    return deferred.promise();
  };

  App.prototype.loadData = function(){
    var _this = this;
    var uid = this.opt.uid;
    var url = uid + "/" + uid + ".json";
    var deferred = $.Deferred();
    $.getJSON(url, function(data) {
      console.log("Loaded data with "+data.sprites.length+" sprites")
      deferred.resolve(data);
    });
    return deferred.promise();
  };

  App.prototype.loadListeners = function(){
    var _this = this;
    var listening = false;

    $(window).on("resize", function(){ _this.onResize(); });
    $(document).on("mousedown", function(e){ e.preventDefault(); listening = true; });
    $(document).on("mouseup", function(e){ listening = false; });
    $(document).on("mousemove", function(e){ if (listening) { _this.play(e); } });
  };

  App.prototype.loadUI = function(options){
    this.imageW = options.width;
    this.imageH = options.height;
    this.cols = options.cols;
    this.rows = options.rows;

    var imageUrl = this.opt.uid + "/" + options.image;

    this.$image = $('<img src="'+imageUrl+'" alt="Matrix of scenes from video" />');
    this.$imageWrapper = $('#image');
    this.$imageWrapper.append(this.$image);

    this.$label = $("#label");

    this.onResize();
  };

  App.prototype.onReady = function(){
    console.log("Ready.");

    this.loadListeners();
  };

  App.prototype.onResize = function(){
    this.width = $(window).width();
    this.height = $(window).height();

    var screenRatio = this.width / this.height;
    var imgRatio = this.imageW / this.imageH;

    // image is wider than screen
    if (imgRatio > screenRatio) {
      var imageH = this.width / imgRatio;
      var top = (this.height - imageH) * 0.5;
      this.$imageWrapper.css({
        "width": "100%",
        "height": imageH + "px",
        "left": 0,
        "top": top + "px"
      });
      this.imageRW = this.width;
      this.imageRH = imageH;

    // image is taller than screen
    } else {
      var imageW = this.height * imgRatio;
      var left = (this.width - imageW) * 0.5;
      this.$imageWrapper.css({
        "height": "100%",
        "width": imageW + "px",
        "left": left + "px",
        "top": 0
      });
      this.imageRH = this.height;
      this.imageRW = imageW;
    }

    this.imageOffset = this.$imageWrapper.offset();
    this.cellW = this.imageRW / this.cols;
    this.cellH = this.imageRH / this.rows;
    this.$label.css({
      "width": this.cellW + "px",
      "height": this.cellH + "px"
    });
  };

  App.prototype.play = function(e){
    var parentOffset = this.imageOffset;
    var x = e.pageX - parentOffset.left;
    var y = e.pageY - parentOffset.top;
    var imgW = this.imageRW;
    var imgH = this.imageRH;

    // check for out of bounds
    if (x < 0 || y < 0 || x >= imgW || y >= imgH) return;

    var cellW = this.cellW;
    var cellH = this.cellH;

    var col = Math.floor(x / cellW);
    var row = Math.floor(y / cellH);

    // move the label
    var cx = col * cellW;
    var cy = row * cellH;
    this.$label.css("transform", "translate3d("+cx+"px, "+cy+"px, 0)");

    // play the cell if not already playing
    var id = row + "-" + col;
    if (this.currentCell !== id) {
      var fileIndex = this.spriteLookup[id];
      var sound = this.sounds[fileIndex];
      sound.play(id);
      this.currentCell = id;
    }
  };

  return App;

})();

$(function() {
  var app = new App({});
});

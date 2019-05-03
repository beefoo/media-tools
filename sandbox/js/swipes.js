'use strict';

// Reference: https://codepen.io/s/pen/ZbgemZ
var SwipesApp = (function() {

  var opt, $container, app;
  var rectW, rectH, rects, positions, rectTemplate, rectRadius;
  var offsets, currentOffsetIndex;

  function SwipesApp(config) {
    var defaults = {
      gridW: 128,
      gridH: 128,
      margin: 0.5,
      frequency: 2,
      radius: 4.0,
      rotationDur: 8000
    };
    opt = $.extend({}, defaults, config);
    init();
  }

  function ease(n) {
    return (Math.sin((n+1.5)*Math.PI)+1.0) / 2.0;
  }


  function norm(value, a, b){
    var denom = (b - a);
    if (denom > 0 || denom < 0) {
      return (1.0 * value - a) / denom;
    } else {
      return 0;
    }
  }

  function translatePoint(p, radians, distance) {
    var x2 = p[0] + distance * Math.cos(radians);
    var y2 = p[1] + distance * Math.sin(radians);
    return [x2, y2];
  }

  function init() {
    $container = $("#app");
    var w = $container.width();
    var h = $container.height();

    app = new PIXI.Application({
      width: w,
      height: h,
      backgroundColor: 0x000000,
      resolution: 1
    });
    $container.append(app.view);

    var cellW = w / opt.gridW;
    var cellH = h / opt.gridH;
    var rectW = cellW - opt.margin * 2;
    var rectH = cellH - opt.margin * 2;
    rectRadius = rectH * opt.radius;
    rectTemplate = new PIXI.Graphics().beginFill(0xFFFFFF).drawRect(-rectW/2, -rectH/2, rectW, rectH);

    rects = [];
    positions = [];
    var offsetsN = [], offsetsNE = [], offsetsE = [], offsetsSE = [];
    for(var row=0; row<opt.gridH; row++) {
      for(var col=0; col<opt.gridW; col++) {
        var rect = new PIXI.Graphics(rectTemplate.geometry);
        rect.tint = Math.random() * 0xFFFFFF;
        app.stage.addChild(rect);
        var x = col * cellW + opt.margin + rectW/2;
        var y = row * cellH + opt.margin + rectH/2;
        positions.push([x, y]);
        rects.push(rect);

        // south to north, offsets are based on row
        var n = 1.0 * (row+col) / (opt.gridH+opt.gridW-2) * 2 * Math.PI * opt.frequency;
        offsetsN.push(n);

        // offsetsNE[i] = ;
        // offsetsE[i] = ;
        // offsetsSE[i] = ;
      }
    }
    offsets = [offsetsN, offsetsNE, offsetsE, offsetsSE];
    currentOffsetIndex = 0;

    app.ticker.add(render);
  }

  function render(deltaTime){
    var now = new Date().getTime();
    var offset = offsets[currentOffsetIndex];
    var nprogress = (now % opt.rotationDur) / opt.rotationDur;
    var radians = (1.0 - nprogress) * 2.0 * Math.PI;

    for(var i=0; i<rects.length; i++) {
      var rect = rects[i];
      var pos = positions[i];
      var roffset = offset[i];
      var rradians = radians + roffset;
      var tpos = translatePoint(pos, rradians, rectRadius);
      rect.x = tpos[0];
      rect.y = tpos[1];
    }
  }

  return SwipesApp;

})();

$(function() {
  var app = new SwipesApp({});
});

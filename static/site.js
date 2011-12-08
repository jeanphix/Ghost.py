(function() {
    var codes = document.getElementsByTagName('code');
    for (var i = 0, len = codes.length; i < len; i++) {
        hljs.highlightBlock(codes[i]);
    }
})();
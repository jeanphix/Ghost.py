/**
* This file includes client side javascript utilities.
*/
var GhostUtils = {
    /**
    * Clicks element for given selector.
    *
    * @param  String  selector  A CSS3 selector that targets the element
    */
    click: function(selector) {
        var elem = document.querySelector(selector);
        if (!elem) {
            return false;
        }
        var evt = document.createEvent("MouseEvents");
        evt.initMouseEvent("click", true, true, window, 1, 1, 1, 1, 1,
            false, false, false, false, 0, elem);
        if (elem.dispatchEvent(evt)) {
            return true;
        }
        return false;
    }
};

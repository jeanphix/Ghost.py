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
    },
    /**
    * Fire method on element matching given selector.
    *
    * @param  String  selector  A CSS3 selector that targets the form to fill.
    * @param  String  method    The name of the method to fire.
    */
    fireOn: function(selector, method) {
        var element = document.querySelector(selector);
        if (!element) {
            throw "Can't find element.";
        }
        return element[method]();
    }
};

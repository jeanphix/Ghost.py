/**
* This file includes client side javascript utilities.
*/
var CasperUtils = {
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
    * Fills form with given values for given selector.
    *
    * @param  String  selector  A CSS3 selector that targets the form to fill.
    * @param  Array   values    The values for each field.
    */
    fill: function(selector, values){
        var form = document.querySelector(selector);
        if (!form) {
            return false;
        }
        for (var name in values) {
            this.setFieldValue(
                document.querySelector('[name="' + name + '"]'),
                values[name]
            );
        }
    },
    /**
    * Sets form field value.
    *
    * @param  HTMLElement  field  The field.
    * @param  Mixed        value  The value to fill in.
    */
    setFieldValue: function(field, value) {
        console.log(value);
    }
};

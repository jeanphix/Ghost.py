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
            this.setFieldValue(name, values[name]);
        }
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
    },
    /**
    * Sets form field value.
    *
    * @param  String  field  The field name.
    * @param  Mixed   value  The value to fill in.
    */
    setFieldValue: function(fieldName, value) {
        var field = document.querySelector('[name="' + fieldName + '"]');
        if (!field || !field instanceof HTMLElement) {
            throw 'Error: Invalid field ' + fieldName;
        }
        var nodeName = field.nodeName.toLowerCase();
        switch (nodeName) {
            case 'input':
                var type = field.type || "text";
                    switch (type) {
                        case "color":
                        case "date":
                        case "datetime":
                        case "datetime-local":
                        case "email":
                        case "hidden":
                        case "month":
                        case "number":
                        case "password":
                        case "range":
                        case "search":
                        case "tel":
                        case "text":
                        case "time":
                        case "url":
                        case "week":
                            field.value = value;
                            break;
                        case "radio":
                            var radios = document.querySelectorAll('[name=' + fieldName + ']');
                            Array.prototype.forEach.call(radios, function(e) {
                                e.checked = (e.value === value);
                            });
                            break;
                        case "checkbox":
                            field.setAttribute('checked', value ? "checked" : "");
                            break;
                    }
                break;

            case 'textarea':
                field.value = value;
                break;

            default:
                throw 'unsupported field type: ' + nodeName;
        }
    }
};

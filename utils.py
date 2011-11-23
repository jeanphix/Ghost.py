class ClientUtils():

    @staticmethod
    def click(selector):
        return """
            var elem = document.querySelector("%s");
            if (!elem) {
                return false;
            }
            var evt = document.createEvent("MouseEvents");
            evt.initMouseEvent("click", true, true, window, 1, 1, 1, 1, 1, false, false, false, false, 0, elem);
            if (elem.dispatchEvent(evt)) {
                return true;
            }
            return false;
            """ % selector

    @staticmethod
    def find_one(selector):
        return """document.querySelector("%s");"""

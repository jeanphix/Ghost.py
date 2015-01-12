/*globals alert, confirm, prompt*/
var promptValue = null,
    result = false;

window.addEventListener('DOMContentLoaded', function () {
    "use strict";
    var alertButton = document.getElementById('alert-button'),
        confirmButton = document.getElementById('confirm-button'),
        promptButton = document.getElementById('prompt-button'),
        updateListButton = document.getElementById('update-list-button');

    alertButton.addEventListener('click', function (e) {
        alert('this is an alert');
        e.preventDefault();
    }, false);

    confirmButton.addEventListener('click', function (e) {
        if (confirm('this is a confirm')) {
            alert('you confirmed!');
        } else {
            alert('you denied!');
        }
        e.preventDefault();
    }, false);

    promptButton.addEventListener('click', function (e) {
        promptValue = prompt("Prompt ?");
        e.preventDefault();
    }, false);

    updateListButton.addEventListener('click', function (e) {
        var request = new XMLHttpRequest();
        request.onreadystatechange = function () {
            if (this.readyState === this.DONE) {
                var data = JSON.parse(this.response),
                    list = document.getElementById('list');
                data.items.forEach(function (item) {
                    var li = document.createElement('li');
                    li.innerHTML = item;
                    list.appendChild(li);
                });
            }
        };
        request.open('GET', updateListButton.href, true);
        request.send(null);
        e.preventDefault();
    }, false);

    window.setTimeout(
        function () {
            window.result = true;
        },
        3000
    );
}, false);

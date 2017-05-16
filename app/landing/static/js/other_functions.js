$(function() {
      $('a#submit_res').bind('click', function() {
        $.getJSON('/SearchResult', {
          searchbar: $('input[name="searchbar"]').val(),
        }, function(data) {
          $("#result_1").text(data.result);
        });
        return false;
      });
    });
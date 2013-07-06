/* -*-Javascript-*-
********************************************************************************
*
* File:         dpdq.js
* RCS:          $Header: $
* Description:  dpdq javascript.
* Author:       Staal Vinterbo
* Created:      Fri Jul  5 11:15:36 2013
* Modified:     Fri Jul  5 22:24:21 2013 (Staal Vinterbo) staal@mats
* Language:     Javascript
* Package:      N/A
* Status:       Experimental
*
* (c) Copyright 2013, Staal Vinterbo, all rights reserved.
*
* dpdq.js is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* dpdq.js is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with dpdq.js; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*
********************************************************************************
*/

/* 
 * ** helpers **
 */
function forEach(array, action) {
    for (var i = 0; i < array.length; i++)
	action(array[i]);
}

function reduce(combine, base, array) {
    forEach(array, function (element) {
	base = combine(base, element);
    });
    return base;
}

function map(fun, array) {
    var a = [];
    forEach(array, function (element) {
	a.push(fun(element));
    });
    return a;
}

function ftos(x, n) {
    var z = Math.pow(10, n)
    return Math.round(x * z)/z
}

/* 
 * ** functions for the interface **
 */

// when clicking an operator in a conjunction descriptor
function oponclick(elm) {
    var ul = elm.parent().find('ul.olist')
    //console.log('clicked ' + $(elm).text())
    $(ul).show()
    var menu = ul.menu( {
	select : function( event, ui ) {
            //console.log('pressed: ' + ui.item.text())
            $(this).parent().find('.operator').text(ui.item.text())
            $(this).hide()
	}
    })
}

// when clicking a value in a conjunction descriptor
function valonclick(elm) {
    var ul = elm.parent().find('ul.vlist')
    //console.log('clicked ' + $(elm).text())
    $(ul).show()
    var menu = ul.menu( {
	select : function( event, ui ) {
            //console.log('pressed: ' + ui.item.text())
            $(this).parent().find('.value').text(ui.item.text())
            $(this).hide()
	}
    })
}

// clicking the "clear selected" button to clear
// descriptors or attributes from the currently selected
// area
function clearsel() {
    $('.selected').find('.pickable').remove()
    $('.selected').find('.descriptor').remove()
}

// when press the 'Delete' button in a
// conjunction created by pressing the 'Create new ...' button
function delcon(elm) {
    $(elm).closest('.css-cell').remove()
}

// when clicking Clear output button
function clearoutput() {
    $('#output').children().remove()
}

// when pressing the 'Create new conjunction' button
function newcon(elm) {
    var x = $('#css-cell').clone()
    x.find('.descriptor').remove()
    x.find('.selectable').removeAttr('id')
    x.find('.selectable').removeClass('selected')
    x.find('.negated-checkbox').after($('<button onclick="delcon($(this))">Delete</button>'))
    x.click( function() {
	$('.selected').removeClass('selected');
	$(this).find('.selectable').addClass('selected');
    });
    $('#c-row').append(x)
}

// when pressing the 'Turn [on/off] popup help.' button
// When using jqueryui.button, the text gets put into a
// span
function toggletooltip() {
    if ( $(document).tooltip("option", "disabled") ) {
	$(document).tooltip("option", "disabled", false)
	$('#tooltip span').text('Turn off balloon help')
    } else {
	$(document).tooltip("option", "disabled", true)
	$('#tooltip span').text('Turn on balloon help')
    }
}

// collect conjunctions contents into predicate list
function getpred() {
    var plist = [];

    forEach($('.conjunction'), function(con) {
	//console.log('con' + con)
	var clist = []
	forEach($(con).find('.descriptor'), function(des) {
            //console.log('des' + des)
            clist.push([$(des).find('.attribute').text(),
			$(des).find('.operator').text(),
			$(des).find('.value').text() + $(des).find('.value').val()])
	});
	if (clist.length) {
            var bit = 0;
            if ($(con).find('.negated').prop('checked')) bit = 1;
            plist.push([bit, clist])
	}
    });
    return plist;
}

// collect processor parameters into list
function getparms() {
    return map(function(par) {
	return [$(par).find('.name').text(),
		$(par).find('input').val()]
    }, $('.parameter'));
}

// collect query into object
function getinfo() {
    return {
	dataset : $('.dataset.picked').text(),
	processor : $('.processor.picked').text(),
	attributes : map(function(s) { return $(s).text() },
                         $('#selected').children()),
	predicate : getpred(),
	parameters : getparms(),
	eps : $('#eps').val(),
	request : 'info'
    }
}

function postinfo() {
    $.ajax({
	// the URL for the request
	url: "",

	// the data to send (will be converted to a query string)
	data: { info : JSON.stringify(getinfo()) },

	// whether this is a POST or GET request
	type: "POST",

	// the type of data we expect back
	dataType : "json",


	// code to run if the request succeeds;
	// the response is passed to the function
	// expecting response to have fields:
	//  status : the QPResponse.status 
	//  html   : a text that can be rendered in the text output panel
	success: function( json ) {

            // scroll output to top of this result
            var osh = $("#output")[0].scrollHeight
            var lc = $('#output').children(':last')
            $('#output').append(json.html)
            var sh = $("#output")[0].scrollHeight
            var h = Math.round($('#output').outerHeight(includeMargin=true) + 0.5)
            if (sh > h) {
		if (osh <= h){
		    $("#output").scrollTop(lc.outerHeight(true));
		} else {
		    $("#output").scrollTop(osh);
		}
            }

            if (json.status != 0) {
		alert('Query unsuccessful, please check output window for explanation.')
            } else {
		// increment risk total
		var val = parseFloat($('#risk-pb').progressbar('value'))
		var eps = parseFloat($('#eps').val())
		//console.log('current value: ' + val)
		//console.log('adding: ' + eps)
		//console.log(' = ', val + eps)
		$('#risk-pb').progressbar('value', val + eps)
		$('#risk-total-current').text(ftos(val+eps,3))
            }
	},

	// code to run if the request fails; the raw request and
	// status codes are passed to the function
	error: function( xhr, status , err) {
            alert( "Sorry, something went wrong. " + status + ' ' + err);
	},

    });
}


  /* 
   * ** jQuery initialization **
   */
function initdpdq() {
    // needed for selection of attribute input pane
    $('#selected').addClass('selected')
    $('.selectable').click( function() {
	$('.selected').removeClass('selected');
	$(this).addClass('selected');
    });
    
    // show descriptions 
    $(document).tooltip();

    // the selection tabs
    $('#box-tabs').tabs({ beforeLoad: function( event, ui ) {
	var s = ui.ajaxSettings.url
	var t = s[s.length - 1]
	if (t == 'a') {
            ui.ajaxSettings.url += '&a=' + $('.dataset.picked').text().trim()
	}
	if (t == 'p') {
            ui.ajaxSettings.url += '&a=' + $('.processor.picked').text().trim()
	}
	ui.jqXHR.error(function() {
            ui.panel.html("Sorry. Could not load this panel.");
	});
    }, load: function( event, ui ) {
        // double click in attribute list
        /* $(ui.panel).find('li').dblclick(function() { */
        $(ui.panel).find('li').on("click", function() {
            // where do we send?
            if ($('.selected').hasClass('conjunction')) {
		// conjunction, so we have to ask for a descriptor
		var dset = $('.picked.dataset').text().trim()
		var attr = $(this).text().trim()
		//console.log('descriptor for ' + dset + ', ' + attr)
		$.get("?q=d&a=" + dset + '&b=' + attr, function(resp) {
		    var x = $(resp);
		    x.find('.attribute').on("click",
					    function() {
						$(this).closest('.descriptor').remove() });
		    $('.selected').append(x);
		});
            }
            else
            {
		// selected attributes box
		if ($.inArray($(this).text(),
                              map(function(x) {return $(x).text()},
				  $('.selected li'))) == -1){
		    // is not already in the box
		    var x = $($(this).clone())
		    x[0].title = "Select to remove."
		    x.on("click", function() { $(this).remove() })
		    $('.selected').append(x);
		}
            }
        })
    }
			});
    
    // initialize selected dataset and processor
    var li_d = $('#tabs-data li:first')
    var li_p = $('#tabs-proc li:first')
    li_d.addClass("picked")
    li_p.addClass("picked")
    $('#status-line .dataset').text(li_d.text().trim())
    $('#status-line .processor').text(li_p.text().trim())
    
    // needed for picking attributes for either the output set
    // or predicate conjunction descriptors
    $('.pickable').click( function() {
	var elm = this;
	
	// clear selected and conjunctions when switching datasets
	if ($(elm).hasClass('dataset')) {
            $('.selectable').find('.pickable').remove()
            $('.selectable').find('.descriptor').remove()
	}

	// clear parameter tab when switching query types
	if ($(elm).hasClass('processor')) {
            $('.parameter').remove()
	}
        
	forEach(['dataset', 'processor', 'attribute', 'parameter'], function(cls) {
            if ( $(elm).hasClass(cls) ){
		$('.' + cls + '.picked').removeClass('picked')
		$(elm).addClass('picked')
		var sl = $('#status-line span.' + cls)
		if (sl.length > 0) {
                    sl.text($(elm).text().trim()) // set statusline
		}
            }
	});
    });

    // initialize risk
    // expected JSON {"tt": 10.0, "total": 0.0, "qt": 3.0}
    $.getJSON("?q=r", function(resp) {
	$('#eps').spinner(
            { min : 0.001,
              max : resp.qt,
              step: 0.01 } )
	//console.log(resp)
	$('#risk-pb').progressbar( { max : resp.tt, value : resp.total })
	$('#risk-total-current').text(ftos(resp.total,3))
	$('#risk-total-max').text(resp.tt)
	$('#eps')[0].title = 'Max per query: ' + resp.qt
    });

    // help button
    $( "#help" ).dialog({
	autoOpen: false, height: 400, width: 600
    });
    $( "#help-button" ).click(function() {
	$( "#help" ).dialog( "open" );
	$('#help').scrollTop(0);
    });
    
    $('button').button()

}

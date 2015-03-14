var gn_lat = {{ gn["loc"][0] }};
var gn_long = {{ gn["loc"][1] }};
{% if locations[direction]["int"] is not none -%}
    var int_lat = {{ locations[direction]["int"]["loc"][0] }};
    var int_long = {{ locations[direction]["int"]["loc"][1] }};
{%- endif %}
var dest_lat = {{ locations[direction]["loc"][0] }};
var dest_long = {{ locations[direction]["loc"][1] }};

function toggleCollapse(id) {
    var el = document.getElementById(id).children[1];
    el.classList.toggle('collapsed');
}

function hideDest() {
    toggleCollapse('dest2gn');
    {% if locations[direction]["int"] is not none -%}
        toggleCollapse('dest2int');
        toggleCollapse('int2gn');
    {%- endif %}
}
function hideGn() {
    toggleCollapse('gn2dest');
    {% if locations[direction]["int"] is not none -%}
        toggleCollapse('int2dest');
        toggleCollapse('gn2int');
    {%- endif %}
}

function hideUnrelevant(position) {
    var lat = position.coords.latitude;
    var long = position.coords.longitude;
    
    var gn_dist = Infinity;
    var int_dist = Infinity;
    var dest_dist = Infinity;

    // On such distance we can assume that Earth is discworld
    gn_dist = Math.sqrt(Math.pow(lat - gn_lat, 2) + Math.pow(long - gn_long, 2));
    {% if locations[direction]["int"] is not none -%}
        int_dist = Math.sqrt(Math.pow(lat - int_lat, 2) + Math.pow(long - int_long, 2));
    {%- endif %}
    dest_dist = Math.sqrt(Math.pow(lat - dest_lat, 2) + Math.pow(long - dest_long, 2));

    if (gn_dist < int_dist && gn_dist < dest_dist) {
        document.getElementById("location").innerHTML += "{{ gn["name_gen"] }}";
        hideDest();
    } else if (int_dist < dest_dist) {
        document.getElementById("location").innerHTML += "{{ locations[direction]["int"]["name_gen"] }}";
    } else {
        document.getElementById("location").innerHTML += "{{ locations[direction]["name_gen"] }}";
        hideGn();
    }
    document.getElementById("coords").innerHTML = lat + ", " + long;
}

if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(hideUnrelevant, function(){});
}

/* static/js/script.js */

// App Download Confirmation
function confirmDownload(event) {
    var check = confirm("क्या आप त्रिकाल दर्शन App डाउनलोड करना चाहते हैं?");
    if (!check) { event.preventDefault(); return false; }
    return true;
}

// City Search with Nominatim
let timeout = null;
function searchCity() {
    clearTimeout(timeout);
    let query = document.getElementById('citySearch').value;
    let resultsDiv = document.getElementById('cityResults');
    if(query.length < 3) { resultsDiv.style.display = 'none'; return; }
    timeout = setTimeout(() => {
        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`)
        .then(res => res.json())
        .then(data => {
            let html = '';
            if(data.length === 0) html = '<div class="city-option">कोई शहर नहीं मिला</div>';
            else {
                data.forEach(place => {
                    let shortName = place.display_name.split(',')[0];
                    html += `<div class="city-option" onclick="selectCity('${shortName.replace(/'/g, "\\'")}', '${place.lat}', '${place.lon}', '${place.display_name.replace(/'/g, "\\'")}')">${place.display_name}</div>`;
                });
            }
            resultsDiv.innerHTML = html;
            resultsDiv.style.display = 'block';
        });
    }, 600);
}

function selectCity(shortName, lat, lon, fullName) {
    document.getElementById('citySearch').value = fullName;
    document.getElementById('city_name').value = shortName;
    document.getElementById('lat').value = lat;
    document.getElementById('lon').value = lon;
    document.getElementById('cityResults').style.display = 'none';
}

function validateForm() {
    if(!document.getElementById('lat').value) { alert("कृपया लिस्ट में से सही शहर चुनें!"); return false; }
    return true;
}

// Panchang Info Modals
function showInfo(key) {
    const infoData = {
        'rahukaal': { title: '🔴 राहुकाल', body: 'अशुभ समय। नए और शुभ कार्य करने से बचें।' },
        'yamaganda': { title: '🟠 यमगंड', body: 'असफलता का सूचक। महत्वपूर्ण कार्यों के लिए टाले।' },
        'gulika': { title: '🟢 गुलिक', body: 'पुनरावृत्ति का समय। शुभ कार्यों के लिए अच्छा है।' },
        'abhijit': { title: '🔵 अभिजित', body: 'विजय मुहूर्त। सभी दोषों को नष्ट करने वाला।' }
    };
    document.getElementById('modalHeader').innerHTML = infoData[key].title;
    document.getElementById('modalBody').innerHTML = infoData[key].body;
    document.getElementById('infoModal').style.display = "block";
}

function closeModal() { document.getElementById('infoModal').style.display = "none"; }

window.onclick = function(event) {
    if (event.target == document.getElementById('infoModal')) closeModal();
}

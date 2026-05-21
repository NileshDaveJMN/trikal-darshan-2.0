# views/seo_views.py
from django.http import HttpResponse
from django.urls import reverse
from datetime import datetime

def sitemap_xml(request):
    url_names = ['home', 'panchang', 'contact', 'login', 'register', 'milan']
    domain = "https://trikaldarshan.pythonanywhere.com"
    pages = []
    
    now = datetime.now().strftime('%Y-%m-%d')
    for name in url_names:
        pages.append({
            'loc': f"{domain}{reverse(name)}",
            'lastmod': now
        })

    xml_output = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_output += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        xml_output += f"  <url>\n    <loc>{page['loc']}</loc>\n    <lastmod>{page['lastmod']}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>\n"
    xml_output += '</urlset>'
    return HttpResponse(xml_output, content_type="application/xml")

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

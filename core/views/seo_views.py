def sitemap_xml(request):
    url_names = ['home', 'panchang', 'milan', 'contact', 'login', 'register']
    
    # ✅ Auto-detect domain from request — works on any server!
    domain = f"{request.scheme}://{request.get_host()}"
    
    priorities = {
        'home': ('1.0', 'daily'),
        'panchang': ('0.9', 'daily'),
        'milan': ('0.9', 'monthly'),
        'contact': ('0.5', 'monthly'),
        'login': ('0.4', 'monthly'),
        'register': ('0.4', 'monthly'),
    }
    
    pages = []
    now = datetime.now().strftime('%Y-%m-%d')
    
    for name in url_names:
        priority, freq = priorities.get(name, ('0.5', 'monthly'))
        pages.append({
            'loc': f"{domain}{reverse(name)}",
            'lastmod': now,
            'priority': priority,
            'changefreq': freq
        })

    xml_output = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_output += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        xml_output += f"""  <url>
    <loc>{page['loc']}</loc>
    <lastmod>{page['lastmod']}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>\n"""
    xml_output += '</urlset>'
    return HttpResponse(xml_output, content_type="application/xml")


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /django-admin/",
        "Disallow: /profile/",
        "Disallow: /onboarding/",
        "Disallow: /api/",
        "Disallow: /telegram-webhook/",
        "Allow: /",
        "",
        # ✅ Tell Google where your sitemap is
        f"Sitemap: https://trikal-darshan.onrender.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
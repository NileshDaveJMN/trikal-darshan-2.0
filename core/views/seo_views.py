def sitemap_xml(request):
    domain = f"{request.scheme}://{request.get_host()}"
    now = datetime.now().strftime('%Y-%m-%d')
    
    pages = []  # ← pages defined here inside function

    # Main pages
    url_names = ['home', 'panchang', 'milan', 'contact', 'login', 'register']
    priorities = {
        'home':     ('1.0', 'daily'),
        'panchang': ('0.9', 'daily'),
        'milan':    ('0.9', 'monthly'),
        'contact':  ('0.5', 'monthly'),
        'login':    ('0.4', 'monthly'),
        'register': ('0.4', 'monthly'),
    }
    for name in url_names:
        priority, freq = priorities.get(name, ('0.5', 'monthly'))
        pages.append({                    # ← must be INSIDE function
            'loc': f"{domain}{reverse(name)}",
            'lastmod': now,
            'priority': priority,
            'changefreq': freq
        })

    # Rashi pages — THIS must also be INSIDE the function
    rashi_ids = ['mesh','vrishabh','mithun','kark','sinh',
                 'kanya','tula','vrishchik','dhanu','makar','kumbh','meen']
    for rashi_id in rashi_ids:
        pages.append({                    # ← inside function ✅
            'loc': f"{domain}/rashifal/{rashi_id}/",
            'lastmod': now,
            'priority': '0.8',
            'changefreq': 'daily'
        })

    # Build XML
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
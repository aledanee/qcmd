import markdown
import os
from jinja2 import Template

def update_documentation():
    # Read the README content
    with open('README.md', 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    # Convert markdown to HTML
    html_content = markdown.markdown(readme_content, extensions=['fenced_code', 'tables'])
    
    # HTML template
    template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>qcmd - AI-powered Command Generator</title>
    <style>
        :root {
            --primary: #3498db;
            --secondary: #2ecc71;
            --accent: #9b59b6;
            --dark: #34495e;
            --light: #ecf0f1;
            --warning: #f39c12;
            --danger: #e74c3c;
            --code-bg: #2d3436;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: var(--light);
        }
        
        header {
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: white;
            padding: 2rem 0;
            text-align: center;
        }
        
        .container {
            width: 90%;
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        pre, code {
            font-family: 'Consolas', 'Monaco', monospace;
            background-color: var(--code-bg);
            color: white;
            border-radius: 4px;
        }
        
        code {
            padding: 0.2rem 0.4rem;
            font-size: 0.9rem;
        }
        
        pre {
            padding: 1rem;
            margin: 1rem 0;
            overflow-x: auto;
        }
        
        h1, h2, h3 {
            color: var(--primary);
            margin: 1.5rem 0 1rem;
        }
        
        a {
            color: var(--primary);
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>qcmd Documentation</h1>
            <p>AI-powered Command Generator using Local LLMs</p>
        </div>
    </header>
    
    <div class="container">
        {{ content }}
    </div>
    
    <footer class="container">
        <p>Last updated: {{ last_updated }}</p>
    </footer>
</body>
</html>
"""
    
    # Create template and render
    template = Template(template_str)
    rendered_html = template.render(
        content=html_content,
        last_updated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Write the output file
    with open('qcmd-docs.html', 'w', encoding='utf-8') as f:
        f.write(rendered_html)

if __name__ == '__main__':
    import datetime
    update_documentation()
    print("Documentation updated successfully!")
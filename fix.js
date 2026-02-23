const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');

const newHtml = html.replace(/className=\{`(.*?)`\}/gs, (match, p1) => {
    let fixed = p1.replace(/\s+-\s+/g, '-')
        .replace(/\s+\/\s+/g, '/')
        .replace(/hover:\s+/g, 'hover:')
        .replace(/focus:\s+/g, 'focus:')
        .replace(/disabled:\s+/g, 'disabled:');
    return `className={\`${fixed}\`}`;
}).replace(/style=\{\{(.*?)\}\}/gs, (match, p1) => {
    let fixed = p1.replace(/\s+-\s+/g, '-');
    return `style={{${fixed}}}`;
});

fs.writeFileSync('index.html', newHtml, 'utf8');
console.log('Fixed index.html class names and styles.');

// Tailwind v3.4.17 (same version the site used from cdn.tailwindcss.com), default theme.
// Rebuild css/tailwind.css after changing classes in HTML or JS (see README):
//   npx tailwindcss@3.4.17 -c tools/tailwind.config.js -i tools/tailwind.input.css -o css/tailwind.css --minify
module.exports = {
  content: ["./*.html", "./award/*.html", "./ticker/*.html", "./guides/*.html", "./js/*.js"],
  theme: { extend: {} },
  plugins: [],
};

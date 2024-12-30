// @ts-check

/** @type {import('postcss-load-config').Config} */
module.exports = {
  plugins: {
    tailwindcss: require('tailwindcss'),
    autoprefixer: require('autoprefixer'),
  }
};

/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#0095f6", // Instagram Blue
                "primary-hover": "#1877f2",

                // Light Mode Defaults
                bg: "#fafafa",
                surface: "#ffffff",
                text: "#262626",
                "text-secondary": "#8e8e8e",
                "text-tertiary": "#c7c7c7",
                border: "#dbdbdb",
            },
            fontFamily: {
                sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
                mono: ['"Fira Code"', 'Consolas', 'monospace'],
            },
            boxShadow: {
                'card': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
            }
        },
    },
    plugins: [],
}

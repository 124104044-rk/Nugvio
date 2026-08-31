const SYMBOLS = { INR: "₹", USD: "$", EUR: "€", GBP: "£" };
export const CURRENCIES = Object.keys(SYMBOLS);

export const getCurrency = () => localStorage.getItem("nugvio_currency") || "INR";
export const setCurrencyLocal = (c) => localStorage.setItem("nugvio_currency", c);
export const sym = () => SYMBOLS[getCurrency()] || "₹";
export const inr = (n) => `${sym()}${Math.round(n).toLocaleString("en-IN")}`;

export const rupees = (n) => (n == null ? "-" : "₹" + Math.round(n).toLocaleString("en-IN"));
export const today = () => new Date().toISOString().slice(0, 10);
export const inDays = (d) => new Date(Date.now() + d * 864e5).toISOString().slice(0, 10);
export const CROPS = ["paddy", "maize", "chilli", "cotton", "banana"];

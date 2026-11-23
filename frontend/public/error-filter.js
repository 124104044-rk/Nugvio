// Suppresses a harmless browser DataCloneError about PerformanceServerTiming.
// Kept as a same-origin file (not inline) so the Content-Security-Policy can forbid inline scripts.
window.addEventListener("error",function(e){if(e.error instanceof DOMException&&e.error.name==="DataCloneError"&&e.message&&e.message.includes("PerformanceServerTiming")){e.stopImmediatePropagation();e.preventDefault()}},true);

// Clean fallback image gradients to avoid 404 errors on missing local assets
const createSvgPlaceholder = (title: string, color1: string, color2: string) =>
  `data:image/svg+xml;utf8,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${color1}"/>
          <stop offset="100%" stop-color="${color2}"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#g)"/>
      <circle cx="400" cy="300" r="180" fill="white" fill-opacity="0.04"/>
      <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="system-ui, sans-serif" font-size="20" fill="white" fill-opacity="0.3">${title}</text>
    </svg>
  `)}`;

export const photos = [
  createSvgPlaceholder("Workspace", "#1e293b", "#0f172a"),
  createSvgPlaceholder("Architecture", "#0f172a", "#1e1b4b"),
  createSvgPlaceholder("Planning", "#1e1b4b", "#172554"),
  createSvgPlaceholder("Meeting", "#172554", "#134e4a"),
  createSvgPlaceholder("Design", "#134e4a", "#1e293b"),
  createSvgPlaceholder("Engineering", "#1e293b", "#312e81"),
  createSvgPlaceholder("Review", "#312e81", "#1e1b4b"),
  createSvgPlaceholder("Documents", "#1e1b4b", "#0f172a"),
  createSvgPlaceholder("Typing", "#0f172a", "#1e293b"),
  createSvgPlaceholder("Notes", "#1e293b", "#172554"),
  createSvgPlaceholder("Team Room", "#172554", "#1e1b4b"),
  createSvgPlaceholder("Office Desk", "#0f172a", "#1e293b"),
  createSvgPlaceholder("Analysis", "#1e293b", "#134e4a"),
  createSvgPlaceholder("Reviewer", "#134e4a", "#0f172a"),
  createSvgPlaceholder("Evaluation", "#0f172a", "#312e81"),
  createSvgPlaceholder("Placement Drive", "#1e1b4b", "#0f172a"),
];

// Small formatting helpers shared across pages.

export function timeAgo(isoDate) {
  if (!isoDate) return "Recently";
  const seconds = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.floor(hours / 24)} d ago`;
}

export function clockTime(isoDate) {
  if (!isoDate) return "";
  return new Date(isoDate).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function fullName(user) {
  if (!user) return "Unassigned";
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  return name || user.username;
}

export function categoryName(category) {
  if (!category) return "General";
  return typeof category === "string" ? category : category.name;
}

export function getCookie(name) {
  const cookies = `; ${document.cookie}`;
  const parts = cookies.split(`; ${name}=`);

  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }

  return "";
}

export function getCSRFToken() {
  return getCookie("csrftoken");
}
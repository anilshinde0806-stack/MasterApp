  import {
  useEffect,
  useRef,
  useState
} from "react";

import "./Menu.css";


function navigateTo(item) {

  if (!item.url) {
    return;
  }


  window.location.href =
    "/"
    + item.url.replace(/^\/+/, "");

}


/* =========================
   SUB MENU ITEM
========================= */

function SubMenuItem({ item }) {

  const [open, setOpen] = useState(false);

  const timerRef = useRef(null);

  const hasChildren =
    item.children &&
    item.children.length > 0;


  function handleMouseEnter() {

    if (timerRef.current) {

      clearTimeout(
        timerRef.current
      );

      timerRef.current = null;

    }


    if (hasChildren) {

      setOpen(true);

    }

  }


  function handleMouseLeave() {

    if (!hasChildren) {

      return;

    }


    timerRef.current =
      setTimeout(() => {

        setOpen(false);

      }, 300);

  }


  useEffect(() => {

    return () => {

      if (timerRef.current) {

        clearTimeout(
          timerRef.current
        );

      }

    };

  }, []);


  return (

    <li
      className={
        `modern-submenu-item ${
          open ? "is-open" : ""
        }`
      }

      onMouseEnter={handleMouseEnter}

      onMouseLeave={handleMouseLeave}
    >

      <button
        type="button"
        className="modern-submenu-link"

        onClick={() => {

          if (!hasChildren) {

            navigateTo(item);

          }

        }}
      >

        {item.icon && (

          <i
            className={item.icon}
          ></i>

        )}


        <span>

          {item.name}

        </span>


        {hasChildren && (

          <i
            className="
              fa-solid
              fa-chevron-right
              modern-sub-arrow
            "
          ></i>

        )}

      </button>


      {hasChildren && open && (

        <ul
          className="modern-nested-menu"

          onMouseEnter={() => {

            if (timerRef.current) {

              clearTimeout(
                timerRef.current
              );

              timerRef.current = null;

            }

          }}

          onMouseLeave={handleMouseLeave}
        >

          {item.children.map(
            (child) => (

              <SubMenuItem
                key={child.id}
                item={child}
              />

            )
          )}

        </ul>

      )}

    </li>

  );

}


/* =========================
   MAIN MENU ITEM
========================= */

function MainMenuItem({
  item,
  isOpen,
  onOpen,
  onClose
}) {

  const timerRef =
    useRef(null);


  const hasChildren =
    item.children &&
    item.children.length > 0;


  function handleMouseEnter() {

    if (timerRef.current) {

      clearTimeout(
        timerRef.current
      );

    }


    if (hasChildren) {

      onOpen();

    }

  }


  function handleMouseLeave() {

    if (!hasChildren) {
      return;
    }


    timerRef.current =
      setTimeout(
        onClose,
        220
      );

  }


  return (

    <li

      className={
        `modern-menu-item ${
          isOpen ? "is-open" : ""
        }`
      }

      onMouseEnter={handleMouseEnter}

      onMouseLeave={handleMouseLeave}

    >

      <button

        type="button"

        className="modern-menu-link"

        onClick={() => {

          if (!hasChildren) {

            navigateTo(item);

          }

        }}

      >

        {item.icon && (

          <i
            className={item.icon}
          ></i>

        )}


        <span>

          {item.name}

        </span>


        {hasChildren && (

          <i className="fa-solid fa-chevron-down modern-menu-arrow"></i>

        )}

      </button>


      {hasChildren && isOpen && (

        <ul
          className="modern-dropdown-menu"

          onMouseEnter={() => {

            if (timerRef.current) {

              clearTimeout(
                timerRef.current
              );

            }

          }}

          onMouseLeave={handleMouseLeave}

        >

          {item.children.map(
            (child) => (

              <SubMenuItem
                key={child.id}
                item={child}
              />

            )
          )}

        </ul>

      )}

    </li>

  );

}


/* =========================
   MENU
========================= */

export default function Menu() {

  const [
    menu,
    setMenu
  ] = useState([]);


  const [
    loading,
    setLoading
  ] = useState(true);


  const [
    error,
    setError
  ] = useState("");


  const [
    openMenu,
    setOpenMenu
  ] = useState(null);


  useEffect(() => {

    async function loadMenu() {

      try {

        setLoading(true);

        setError("");


        const response =
          await fetch(
            "/ajax/react-menu/",
            {
              credentials:
                "same-origin",
            }
          );


        if (!response.ok) {

          throw new Error(
            `HTTP ${response.status}`
          );

        }


        const result =
          await response.json();


        if (!result.success) {

          throw new Error(
            "Unable to load menu"
          );

        }


        setMenu(
          result.menu || []
        );

      } catch (error) {

        console.error(
          "Menu API error:",
          error
        );


        setError(
          "Unable to load menu"
        );

      } finally {

        setLoading(false);

      }

    }


    loadMenu();

  }, []);


  if (loading) {

    return (

      <div className="modern-menu-loading">

        Loading menu...

      </div>

    );

  }


  if (error) {

    return (

      <div className="modern-menu-error">

        {error}

      </div>

    );

  }


  return (

    <nav className="modern-react-menu">

      <ul className="modern-menu-list">


        {/* HOME */}

        <li className="modern-menu-item">

          <button

            type="button"

            className="modern-menu-link modern-home-link"

            onClick={() => {

              window.location.href = "/";

            }}

          >

            <i className="fa-solid fa-house"></i>

            <span>

              Home

            </span>

          </button>

        </li>


        {/* DYNAMIC MENU */}

        {menu.map((item) => (

          <MainMenuItem

            key={item.id}

            item={item}

            isOpen={
              openMenu === item.id
            }

            onOpen={() => {

              setOpenMenu(item.id);

            }}

            onClose={() => {

              setOpenMenu(null);

            }}

          />

        ))}

      </ul>

    </nav>

  );

}
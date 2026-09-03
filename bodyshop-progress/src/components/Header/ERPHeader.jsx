import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import "./ERPHeader.css";

import {
  getCookie
} from "../../utils/csrf";

import ERPMenu from "../Menu/Menu";
export default function ERPHeader() {

  const [data, setData] = useState({
    company: {
      name: "",
      logo: "",
    },

    branch: {
      name: "",
    },

    employee: {
      name: "",
      type: "",
    },
  });


  const [
    notifications,
    setNotifications
  ] = useState([]);


  const [
    notificationCount,
    setNotificationCount
  ] = useState(0);


  const [
    notificationOpen,
    setNotificationOpen
  ] = useState(false);


  const [
    announcements,
    setAnnouncements
  ] = useState([]);


  const [
    announcementOpen,
    setAnnouncementOpen
  ] = useState(false);


  const [
    announcementLoading,
    setAnnouncementLoading
  ] = useState(false);


  const [
    announcementModal,
    setAnnouncementModal
  ] = useState(false);


  const [
    announcementIndex,
    setAnnouncementIndex
  ] = useState(0);


  const notificationRef = useRef(null);

  const announcementRef = useRef(null);
  const [notificationPosition, setNotificationPosition] =
  useState({
    top: 0,
    left: 0,
  });

const [announcementPosition, setAnnouncementPosition] =
  useState({
    top: 0,
    left: 0,
  });
const notificationPanelRef = useRef(null);

const announcementPanelRef = useRef(null);

const [userMenuOpen, setUserMenuOpen] =
  useState(false);

const userMenuRef = useRef(null);

const userMenuPanelRef = useRef(null);
const [userMenuPosition, setUserMenuPosition] = useState({
  top: 0,
  left: 0,
});
  /* =========================
     HEADER DATA
  ========================= */

  useEffect(() => {

    async function loadHeaderData() {

      try {

        const response = await fetch(
          "/ajax/header-data/",
          {
            credentials: "same-origin",
          }
        );


        if (!response.ok) {

          throw new Error(
            `HTTP ${response.status}`
          );

        }


        const result =
          await response.json();


        if (result.success) {

          setData({

            company:
              result.company || {
                name: "",
                logo: "",
              },

            branch:
              result.branch || {
                name: "",
              },

            employee:
              result.employee || {
                name: "",
                type: "",
              },

          });

        }

      } catch (error) {

        console.error(
          "Header API error:",
          error
        );

      }

    }


    loadHeaderData();

  }, []);


  /* =========================
     NOTIFICATIONS
  ========================= */
  function openNotificationPanel() {

  setAnnouncementOpen(false);

  if (notificationRef.current) {

    const rect =
      notificationRef.current.getBoundingClientRect();

    setNotificationPosition({

      top:
        rect.bottom + window.scrollY + 10,

      left:
        Math.max(
          12,
          rect.right + window.scrollX - 360
        ),

    });

  }

  setNotificationOpen(
    previous => !previous
  );

}

function openUserMenu() {

  setNotificationOpen(false);
  setAnnouncementOpen(false);

  if (userMenuRef.current) {

    const rect =
      userMenuRef.current.getBoundingClientRect();

    setUserMenuPosition({

      top: rect.bottom + 8,

      left: rect.right - 210,

    });

  }

  setUserMenuOpen(previous => !previous);

}
function openAnnouncementPanel() {

  setNotificationOpen(false);

  if (announcementRef.current) {

    const rect =
      announcementRef.current.getBoundingClientRect();

    setAnnouncementPosition({

      top:
        rect.bottom + window.scrollY + 10,

      left:
        Math.max(
          12,
          rect.right + window.scrollX - 390
        ),

    });

  }

  setAnnouncementOpen(
    previous => !previous
  );

  loadAnnouncements();

}
  async function loadNotifications() {

    try {

      const response = await fetch(
        "/ajax/unread-notifications/",
        {
          credentials: "same-origin",
        }
      );


      if (!response.ok) {

        throw new Error(
          `HTTP ${response.status}`
        );

      }


      const result =
        await response.json();


      setNotificationCount(
        result.count || 0
      );


      setNotifications(
        result.notifications || []
      );

    } catch (error) {

      console.error(
        "Notification loading error:",
        error
      );

    }

  }


  useEffect(() => {

    loadNotifications();


    const interval =
      setInterval(
        loadNotifications,
        30000
      );


    return () => {

      clearInterval(interval);

    };

  }, []);


  async function markNotificationRead(
    notification
  ) {

    try {

      const csrfToken =
        getCookie("csrftoken");


      const response = await fetch(

        `/ajax/notification/${notification.id}/read/`,

        {
          method: "POST",

          credentials: "same-origin",

          headers: {

            "X-CSRFToken":
              csrfToken,

          },

        }

      );


      if (!response.ok) {

        throw new Error(
          `HTTP ${response.status}`
        );

      }


      setNotifications((previous) =>
        previous.filter(
          (item) =>
            item.id !== notification.id
        )
      );


      setNotificationCount((previous) =>
        Math.max(previous - 1, 0)
      );


      setNotificationOpen(false);


      if (notification.url) {

        window.location.href =
          notification.url;

      }

    } catch (error) {

      console.error(
        "Notification read error:",
        error
      );

    }

  }


  async function markAllNotificationsRead() {

    try {

      const csrfToken =
        getCookie("csrftoken");


      const response = await fetch(

        "/ajax/notifications/read-all/",

        {
          method: "POST",

          credentials: "same-origin",

          headers: {

            "X-CSRFToken":
              csrfToken,

          },

        }

      );


      if (!response.ok) {

        throw new Error(
          `HTTP ${response.status}`
        );

      }


      setNotifications([]);

      setNotificationCount(0);

    } catch (error) {

      console.error(
        "Mark all notifications error:",
        error
      );

    }

  }


  /* =========================
     ANNOUNCEMENTS
  ========================= */

  async function loadAnnouncements() {

    try {

      setAnnouncementLoading(true);


      const response = await fetch(

        "/ajax/unread-announcements/?t="
        + Date.now(),

        {
          credentials: "same-origin",
        }

      );


      if (!response.ok) {

        throw new Error(
          `HTTP ${response.status}`
        );

      }


      const result =
        await response.json();


      const items =
        Array.isArray(result)
          ? result
          : [];


      setAnnouncements(items);

      return items;

    } catch (error) {

      console.error(
        "Announcement loading error:",
        error
      );

      setAnnouncements([]);

      return [];

    } finally {

      setAnnouncementLoading(false);

    }

  }


  useEffect(() => {

    async function checkAnnouncements() {

      const items =
        await loadAnnouncements();


      if (items.length > 0) {

        setAnnouncementIndex(0);

        setAnnouncementModal(true);

      }

    }


    checkAnnouncements();

  }, []);


  async function markAnnouncementRead(
    announcement
  ) {

    try {

      const csrfToken =
        getCookie("csrftoken");


      const response = await fetch(

        `/ajax/announcement/${announcement.id}/read/`,

        {
          method: "POST",

          credentials: "same-origin",

          headers: {

            "X-CSRFToken":
              csrfToken,

          },

        }

      );


      if (!response.ok) {

        throw new Error(
          `HTTP ${response.status}`
        );

      }


      const nextIndex =
        announcementIndex + 1;


      if (
        nextIndex <
        announcements.length
      ) {

        setAnnouncementIndex(
          nextIndex
        );

      } else {

        setAnnouncementModal(false);

        setAnnouncements([]);

        setAnnouncementIndex(0);

      }

    } catch (error) {

      console.error(
        "Announcement read error:",
        error
      );

    }

  }


  /* =========================
     OUTSIDE CLICK
  ========================= */

useEffect(() => {

  function handleOutsideClick(event) {

    /* =========================
       NOTIFICATION
    ========================= */

    const clickedNotificationButton =
      notificationRef.current?.contains(
        event.target
      );

    const clickedNotificationPanel =
      notificationPanelRef.current?.contains(
        event.target
      );

    if (
      !clickedNotificationButton &&
      !clickedNotificationPanel
    ) {
      setNotificationOpen(false);
    }


    /* =========================
       ANNOUNCEMENT
    ========================= */

    const clickedAnnouncementButton =
      announcementRef.current?.contains(
        event.target
      );

    const clickedAnnouncementPanel =
      announcementPanelRef.current?.contains(
        event.target
      );

    if (
      !clickedAnnouncementButton &&
      !clickedAnnouncementPanel
    ) {
      setAnnouncementOpen(false);
    }


    /* =========================
       USER MENU
    ========================= */

    const clickedUserButton =
      userMenuRef.current?.contains(
        event.target
      );

    const clickedUserPanel =
      userMenuPanelRef.current?.contains(
        event.target
      );

    if (
      !clickedUserButton &&
      !clickedUserPanel
    ) {
      setUserMenuOpen(false);
    }

  }


  document.addEventListener(
    "mousedown",
    handleOutsideClick
  );


  return () => {

    document.removeEventListener(
      "mousedown",
      handleOutsideClick
    );

  };

}, []);


  /* =========================
     LOGOUT
  ========================= */

  async function handleLogout() {

    try {

      const csrfToken =
        getCookie("csrftoken");


      const response = await fetch(

        "/logout/",

        {
          method: "POST",

          credentials: "same-origin",

          headers: {

            "X-CSRFToken":
              csrfToken,

            "Content-Type":
              "application/x-www-form-urlencoded",

          },

        }

      );


      if (response.ok) {

        window.location.href = "/";

      }

    } catch (error) {

      console.error(
        "Logout error:",
        error
      );

    }

  }


  /* =========================
     LIVE CLOCK
  ========================= */

  const [
    now,
    setNow
  ] = useState(
    new Date()
  );


  useEffect(() => {

    const timer =
      setInterval(() => {

        setNow(new Date());

      }, 1000);


    return () => {

      clearInterval(timer);

    };

  }, []);


  const dateText =
    now.toLocaleDateString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }
    );


  const timeText =
    now.toLocaleTimeString(
      "en-IN",
      {
        hour: "2-digit",
        minute: "2-digit",
      }
    );


  const currentAnnouncement =
    announcements[
      announcementIndex
    ];


  return (

    <>

      {/* =========================
          TOP SYSTEM BAR
      ========================= */}

      <div className="erp-system-bar">

        <div className="erp-system-left">

          <i className="fa-solid fa-grip"></i>

          <span>
            MasterApp Operating System
          </span>

          <span className="erp-system-divider">
            |
          </span>

          <strong>
            BODYSHOP
          </strong>

        </div>


        <div className="erp-system-right">

          <span>
            {dateText}
          </span>

          <span>
            {timeText}
          </span>

          <span className="erp-online-dot"></span>

        </div>

      </div>


      {/* =========================
          MAIN HEADER
      ========================= */}

      <header className="erp-react-header">

  {/* =========================================
      LEFT : COMPANY
  ========================================= */}

  <div className="erp-header-company">

    {data.company.logo ? (

      <img
        src={data.company.logo}
        alt={data.company.name}
        className="erp-company-logo"
      />

    ) : (

      <div className="erp-company-logo-placeholder">
        🏢
      </div>

    )}


    <div className="erp-company-info">

      <div className="erp-company-name">
        {data.company.name || "Loading..."}
      </div>

      <div className="erp-company-subtitle">
        BODYSHOP
      </div>

    </div>

  </div>


  {/* =========================================
      CENTER : MENU
  ========================================= */}

  <div className="erp-header-menu">

    {/* Your existing React Menu component */}

    <ERPMenu />

  </div>


  {/* =========================================
      RIGHT : BRANCH + NOTIFICATION + USER
  ========================================= */}

  <div className="erp-header-right">


    {/* BRANCH */}

    <button
      type="button"
      className="erp-branch-selector"
    >

      <i className="fa fa-location-dot"></i>

      <span>
        {data.branch.name || "Branch"}
      </span>

      <i className="fa fa-chevron-down"></i>

    </button>


    {/* NOTIFICATIONS */}

    <div
      className="erp-notification-wrap"
      ref={notificationRef}
    >

      <button
    type="button"
    className="erp-notification-btn"
    onClick={openNotificationPanel}
  >

    <i className="fa fa-bell"></i>

    {notificationCount > 0 && (

      <span className="erp-notification-count">

        {notificationCount > 99
          ? "99+"
          : notificationCount}

      </span>

    )}

  </button>

     
    </div>


    {/* ANNOUNCEMENTS */}

    <div
  className="erp-announcement-wrap"
  ref={announcementRef}
>

  <button
    type="button"
    className="erp-header-icon-btn"
    title="Announcements"
    onClick={openAnnouncementPanel}
  >

    <i className="fa fa-bullhorn"></i>

  </button>

</div>


    {/* EMPLOYEE */}

    <div
  className="erp-user-menu-wrap"
  ref={userMenuRef}
>

  <button
    type="button"
    className="erp-employee-profile"
    onClick={openUserMenu}
  >

    <div className="erp-employee-avatar">

      <i className="fa fa-user"></i>

    </div>


    <div className="erp-employee-details">

      <div className="erp-employee-name">

        {data.employee.name}

      </div>


      <div className="erp-employee-type">

        {data.employee.type}

      </div>

    </div>


    <i className="fa fa-chevron-down erp-user-chevron"></i>

  </button>

</div>


    {/* LOGOUT */}

    <button
      type="button"
      className="erp-logout-btn"
      onClick={handleLogout}
      title="Logout"
    >

      <i className="fa fa-sign-out-alt"></i>

    </button>

  </div>

</header>


    {notificationOpen &&

      createPortal(

        <div
            ref={notificationPanelRef}
          className="erp-portal-notification-panel"
          style={{

            top:
              `${notificationPosition.top}px`,

            left:
              `${notificationPosition.left}px`,

          }}
        >

          <div className="erp-notification-header">

            <strong>
              Notifications
            </strong>


            {notificationCount > 0 && (

              <button
                type="button"
                className="erp-read-all"
                onClick={markAllNotificationsRead}
              >

                Read All

              </button>

            )}

          </div>


          <div className="erp-notification-list">

            {notifications.length === 0 ? (

              <div className="erp-notification-empty">

                No new notifications

              </div>

            ) : (

              notifications.map(
                (notification) => (

                  <button
                    key={notification.id}
                    type="button"
                    className="erp-notification-item"

                    onClick={() =>
                      markNotificationRead(
                        notification
                      )
                    }
                  >

                    <strong>
                      {notification.title}
                    </strong>


                    <span>
                      {notification.message}
                    </span>

                  </button>

                )
              )

            )}

          </div>

        </div>,

        document.body

      )

     }
        {announcementOpen &&

      createPortal(

        <div
          ref={announcementPanelRef}
          className="erp-portal-announcement-panel"
          style={{

            top:
              `${announcementPosition.top}px`,

            left:
              `${announcementPosition.left}px`,

          }}
        >

          <div className="erp-announcement-header">

            <strong>
              Announcements
            </strong>

          </div>


          <div className="erp-announcement-list">

            {announcementLoading ? (

              <div className="erp-announcement-empty">

                Loading announcements...

              </div>

            ) : announcements.length === 0 ? (

              <div className="erp-announcement-empty">

                No new announcements

              </div>

            ) : (

              announcements.map(
                (announcement) => (

                  <div
                    key={announcement.id}
                    className="erp-announcement-item"
                  >

                    {announcement.image && (

                      <img
                        src={announcement.image}
                        alt={announcement.title}
                        className="erp-announcement-image"
                      />

                    )}


                    <div className="erp-announcement-content">

                      <strong>
                        {announcement.title}
                      </strong>


                      <span>
                        {announcement.message}
                      </span>


                      <button
                        type="button"
                        className="erp-announcement-read-btn"

                        onClick={() =>
                          markAnnouncementRead(
                            announcement.id
                          )
                        }
                      >

                        Mark as Read

                      </button>

                    </div>

                  </div>

                )
              )

            )}

          </div>

        </div>,

        document.body

      )

     }

     {userMenuOpen &&

  createPortal(

    <div
      ref={userMenuPanelRef}
      className="erp-portal-user-menu"
      style={{
        top: `${userMenuPosition.top}px`,
        left: `${userMenuPosition.left}px`,
      }}
    >

      <div className="erp-user-menu-info">

        <strong>
          {data.employee.name}
        </strong>

        <span>
          {data.employee.type}
        </span>

      </div>


      <div className="erp-user-menu-divider"></div>


      <button
        type="button"
        className="erp-user-menu-item"
      >

        <i className="fa fa-user"></i>

        Profile

      </button>


      <button
        type="button"
        className="erp-user-menu-item erp-user-logout-item"
        onClick={handleLogout}
      >

        <i className="fa fa-sign-out-alt"></i>

        Logout

      </button>

    </div>,

    document.body

  )
}

      {/* =========================
          ANNOUNCEMENT MODAL
      ========================= */}

      {announcementModal &&
        currentAnnouncement && (

          <div className="erp-announcement-modal-overlay">

            <div className="erp-announcement-modal">

              <div className="erp-announcement-modal-header">

                <h5>

                  {currentAnnouncement.title}

                </h5>

                <button
                  type="button"
                  onClick={() =>
                    setAnnouncementModal(false)
                  }
                >

                  ×

                </button>

              </div>


              <div className="erp-announcement-modal-body">

                {currentAnnouncement.image && (

                  <img
                    src={
                      currentAnnouncement.image
                    }
                    alt="Announcement"
                  />

                )}


                {currentAnnouncement.type && (

                  <span className="erp-announcement-type">

                    {currentAnnouncement.type}

                  </span>

                )}


                <p>

                  {currentAnnouncement.message}

                </p>

              </div>


              <div className="erp-announcement-modal-footer">

                <button
                  type="button"
                  onClick={() =>
                    markAnnouncementRead(
                      currentAnnouncement
                    )
                  }
                >

                  I Have Read

                </button>

              </div>

            </div>

          </div>

        )}

    </>

  );

}
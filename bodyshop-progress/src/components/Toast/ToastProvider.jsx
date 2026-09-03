import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import "./Toast.css";


const ToastContext =
  createContext(null);


export function ToastProvider({ children }) {

  const [toasts, setToasts] =
    useState([]);


  function removeToast(id) {

    setToasts((previous) =>
      previous.filter(
        (toast) => toast.id !== id
      )
    );

  }


  function showToast(
    message,
    type = "success",
    duration = 4000
  ) {

    const id =
      Date.now() +
      Math.random();


    const toast = {

      id,

      message,

      type,

    };


    setToasts((previous) => [

      ...previous,

      toast,

    ]);


    if (duration > 0) {

      setTimeout(() => {

        removeToast(id);

      }, duration);

    }


    return id;

  }


  // =====================================
  // DJANGO / LEGACY JAVASCRIPT BRIDGE
  // =====================================

  useEffect(() => {

    window.showMessage = function (
      message,
      type = "success"
    ) {

      showToast(
        message,
        type
      );

    };


    // Optional modern global function

    window.showToast =
      showToast;


    return () => {

      delete window.showMessage;

      delete window.showToast;

    };

  }, []);


  return (

    <ToastContext.Provider
      value={{ showToast }}
    >

      {children}


      {/* ============================
          GLOBAL TOAST CONTAINER
      ============================ */}

      <div className="erp-toast-container">

        {toasts.map((toast) => (

          <div

            key={toast.id}

            className={
              `erp-toast erp-toast-${toast.type}`
            }

          >

            <div className="erp-toast-message">

              {toast.message}

            </div>


            <button

              type="button"

              className="erp-toast-close"

              onClick={() =>
                removeToast(toast.id)
              }

            >

              ×

            </button>

          </div>

        ))}

      </div>


    </ToastContext.Provider>

  );

}


// =====================================
// REACT HOOK
// =====================================

export function useToast() {

  const context =
    useContext(ToastContext);


  if (!context) {

    throw new Error(
      "useToast must be used inside ToastProvider"
    );

  }


  return context;

}
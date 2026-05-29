import React, { createContext, useState, useContext } from 'react';

const AppContext = createContext();

export function AppProvider({ children }) {
  const [pageContext, setPageContext] = useState("The user is currently browsing the BETA-AI Thalassemia Dashboard.");

  return (
    <AppContext.Provider value={{ pageContext, setPageContext }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  return useContext(AppContext);
}

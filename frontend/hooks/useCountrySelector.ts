import { useState, useEffect } from "react";
import { fetchCountries } from "@/lib/api";

export function useCountrySelector(defaultCountry: string = "Global") {
  const [countries, setCountries] = useState<string[]>([]);
  const [selectedCountry, setSelectedCountry] = useState(defaultCountry);

  useEffect(() => {
    fetchCountries()
      .then((data) => setCountries(data.countries))
      .catch((error) => console.error("Failed to load countries:", error));
  }, []);

  return {
    countries,
    selectedCountry,
    setSelectedCountry,
  };
}

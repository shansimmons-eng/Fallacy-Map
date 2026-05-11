import { useEffect, useState } from 'react'
import { useArgumentStore, PublicationMarker } from '../stores/argumentStore'

interface MapPressMarker {
  id: string
  title: string
  lat: number
  lng: number
  color: string
  veracity: number
}

interface MapPressSyncProps {
  manifestUrl?: string
}

export function useMapPressSync(manifestUrl?: string) {
  const [markers, setMarkers] = useState<MapPressMarker[]>([])
  const [loading, setLoading] = useState(false)
  const { jumpToMarker, activeMarker, manifoldJump } = useArgumentStore()
  
  useEffect(() => {
    if (manifestUrl) {
      loadManifest(manifestUrl)
    }
  }, [manifestUrl])
  
  const loadManifest = async (url: string) => {
    setLoading(true)
    try {
      const response = await fetch(url)
      const data = await response.json()
      
      const mapMarkers: MapPressMarker[] = data.markers.map((m: PublicationMarker) => ({
        id: m.id,
        title: m.headline,
        lat: m.lat || 0,
        lng: m.lon || 0,
        color: m.color,
        veracity: m.veracity_score
      }))
      
      setMarkers(mapMarkers)
    } catch (error) {
      console.error('Failed to load manifest:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleMarkerClick = (marker: MapPressMarker) => {
    const pubMarker: PublicationMarker = {
      id: marker.id,
      headline: marker.title,
      source_url: '',
      source_name: '',
      lat: marker.lat,
      lon: marker.lng,
      veracity_score: marker.veracity,
      fallacy_types: [],
      color: marker.color
    }
    jumpToMarker(pubMarker)
  }
  
  return {
    markers,
    loading,
    activeMarker,
    manifoldJump,
    handleMarkerClick,
    loadManifest
  }
}

export function getSunriseColor(veracity: number): string {
  if (veracity > 0.8) return '#FFFFFF'
  if (veracity > 0.5) return '#FFB300'
  if (veracity > 0.3) return '#FF8F00'
  return '#B71C1C'
}
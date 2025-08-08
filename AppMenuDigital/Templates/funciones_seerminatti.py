def nota_final(*notas, dec=2, **pesos):
   

    if not pesos:
        nf = 0
    else:
      
        suma_ponderada = 0
        suma_pesos = 0
        for nota, peso in zip(notas, pesos.values()):
            suma_ponderada += nota * peso
            suma_pesos += peso
        
        
        nf = suma_ponderada / suma_pesos
    
    
    nf_redondeada = round(nf, dec)
    
    
    if nf_redondeada >= 4:
        estado = "Aprobado"
    else:
        estado = "Desaprobado"
    
   
    return nf_redondeada, estado



nf, estado = nota_final(7.2, 8.5, lab=0.6, taller=0.4)
print(nf, estado)  # → 7.80 Aprobado
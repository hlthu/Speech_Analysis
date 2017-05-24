import numpy as np
class Signal():
    def __init__( self, signal, rate ):
        self.signal = signal
        self.rate = rate
        
    def get_F_0( self, min_pitch = 75, max_pitch = 600, max_num_candidates = 2, octave_cost = .01, 
                voicing_threshold = .4, silence_threshold = .01, HNR = False ):
        """
        Compute Fundamental Frequency (F_0).
        Algorithm uses Fast Fourier Transform (FFT) to filter out values higher than the Nyquist Frequency. 
        Then it segments the signal into frames containing at least 3 periods of the minimum pitch.
        For each frame it then again uses FFT to calculate normalized autocorrelation of the signal. 
        After autocorrelation is calculated it is upsampled with sinc interpolation, and smoothed to find 
        the maxima values of the interpolation. After these values have been chosen the best candidate
        for the F_0 is picked and then returned.
        This algorithm is adapted from 
        http://www.fon.hum.uva.nl/david/ba_shs/2010/Boersma_Proceedings_1993.pdf
        
        Args:
            min_pitch (float): minimum value to be returned as pitch, cannot be less than or equal to zero
            max_pitch (float): maximum value to be returned as pitch, cannot be greater than Nyquist Frequency
            max_num_candidates (int): maximum number of candidates to be considered for each frame, unvoiced 
                               candidate (i.e. fundamental frequency equal to zero) is always considered.
            octave_cost (float): value between 0 and 1 that aids in determining which candidate for the frame
                                is best. Higher octave_cost favors higher frequencies.
            voicing_threshold (float): Threshold that peak of autocorrelation of signal must be greater than
                                 to be considered for maxima, and used to calculate strength of voiceless
                                 candidate. The higher the value the more likely the F_0 will be returned as
                                 voiceless.
            silence_threshold (float): Used to calculate strength of voiceless candidate, the higher the value
                                  the more likely the F_0 will be returned as voiceless.
            HNR (bool): boolean determining if HNR is calculated and returned.
            
        Returns:
            float: The F_0 of the signal +/- 2 hz.
            
        Raises:
            TypeError: min_pitch, max_pitch, and max_num_candidates must be an int, octave_cost, silence_threshold, and voicing_threshold must be a float, and HNR must be a bool.
            ValueError: The maximum pitch cannot be greater than the Nyquist Frequency.
            ValueError: The minimum pitch cannot be equal or less than zero.
            ValueError: The minimum number of candidates is 2.
            ValueError: octave_cost must be between 0 and 1.
            ValueError: silence_threshold must be between 0 and 1.
            ValueError: voicing_threshold must be between 0 and 1.
        
        Example:
        ::
            
            from scipy.io import wavfile as wav
            rate, wave= wav.read( 'example_audio_file.wav' )
            sig = Signal( wave, rate )
            sig.get_F_0()
            
        """
        
        time_step=1./self.rate
        total_time = time_step * len( self.signal )
        Nyquist_Frequency = 1. / ( time_step * 2 )
        
        #checking to make sure values are valid
        #check for type errors of values passed in 
        if type( HNR )!= bool :
            raise TypeError( "HNR must be a bool." )
            
        if HNR:
            if ( type( min_pitch ) != int or
                 type( silence_threshold ) != float):
                raise TypeError( "min_pitch must be an int, and silence_threshold must be a float." )
                
        #these are only values we need to check if we are not doing HNR
        else:
            if ( type( min_pitch ) != int or 
                 type( max_pitch ) != int or 
                 type( max_num_candidates ) != int or 
                 type( octave_cost ) != float or 
                 type( silence_threshold ) != float or
                 type( voicing_threshold ) != float ):
                
                raise TypeError( "min_pitch, max_pitch, and max_num_candidates must be an int, octave_cost, silence_threshold, and voicing_threshold must be a float" )   
                   
            if Nyquist_Frequency < max_pitch:
                raise ValueError( "The maximum pitch cannot be greater than the Nyquist Frequency." )
            if max_num_candidates <2 :
                raise ValueError( "The minimum number of candidates is 2.")
            if octave_cost < 0 or octave_cost > 1:
                raise ValueError( "octave_cost must be between 0 and 1." )            
            if voicing_threshold < 0 or voicing_threshold> 1:
                raise ValueError( "voicing_threshold must be between 0 and 1." ) 
                
        #these values need to be checked for F_0 and HNR calculations   
        if min_pitch <= 0:
            raise ValueError( "The minimum pitch cannot be equal or less than zero." )
        if silence_threshold < 0 or silence_threshold > 1:
            raise ValueError( "silence_threshold must be between 0 and 1." )
            
        #filtering by Nyquist Frequency (preproccesing step)
        upper_bound = .95 * Nyquist_Frequency
        fft_signal = np.fft.fft( self.signal )
        fft_signal = fft_signal * ( fft_signal < upper_bound )
        sig = np.fft.ifft( fft_signal )
        
        global_peak = max( abs( sig ) )
        
        #finding the window_len in seconds, finding frame len (as an integer of how many points will be in a window), finding number of frames/ windows that we will need to segment the signal into
        #then segmenting signal
        if HNR: 
            window_len = 6.0 / min_pitch
            octave_cost = 0
            voicing_threshold = 0
            max_pitch = Nyquist_Frequency
        else:
            window_len = 3.0 / min_pitch
        frame_len = window_len / time_step
        num_frames = max( 1, int( len( sig ) / frame_len + .5 ) ) #there has to be at least one frame
        segmented_signal = [ sig[ int( i * frame_len ) : int( ( i + 1 ) * frame_len ) ] for i in range( num_frames + 1 ) ]
        
        #This eliminates an empty list that could be created
        if len( segmented_signal[ len( segmented_signal ) - 1 ] ) == 0:
            segmented_signal = segmented_signal[ : -1 ]
            
        def estimated_autocorrelation( x ):
            """
            This function accepts a signal and calculates an estimation of the autocorrelation, 
            based off the given algorithm, described below.
            1. append half the window length of zeros
            2. append zeros until the segment length is a power of 2, calculated with log.
            3. take the FFT
            4. square samples in the signal
            5. then again take the FFT
            
            Args:
                x (numpy.ndarray): an array of the signal that autocorrelation is calculated from.
            
            Returns: 
                a (numpy.ndarray): an array of the normalized autocorrelation of the signal.
            
            """
            N = len( x )
            x = np.hstack( ( x, np.zeros( int( N / 2 ) ) ) )
            x = np.hstack( ( x, np.zeros( 2 ** ( int( np.log2( N ) + 1 ) ) - N ) ) )            
            s = np.fft.fft( x )
            a = np.real( np.fft.fft( s * np.conjugate( s ) ) )
            a = a[ :N ]
            return a
        
        def sinc_interp( x, s, u ):
            """
            This function uses sinc interpolation to upsample x.
            
            Args:
                x (numpy.ndarray): an array of the signal to be interpolated
                s (numpy.ndarray): an array of the sampled domain
                u (numpy.ndarray): an array of the upsampled domain
                
            Returns:
                y (numpy.ndarray): an array of the upsampled and interpolated signal.
                
            """
            #Find the period    
            T = s[ 1 ] - s[ 0 ]
            #This creates an array of values to use in our interpolation
            sincM = np.tile( u, ( len( s ), 1 ) ) - np.tile( s[ :, np.newaxis ], ( 1, len( u ) ) )
            #This calculates interpolated array
            y = np.dot( x, np.sinc( sincM / T ) )
            return y
         
        def find_max( arr, time_array ):
            """
            This function finds multiple maxima of an array.
            It calculates the multiple peaks by:
            1. setting the nonpositive elements of the array equal to zero
            2. segmenting the signal into the different positive portions
            3. taking the first max_num_candidates-1 segments and using the maximum value of each segment as the peak.
            
            Args:
                arr (numpy.ndarray): an array of the signal we are calculating the peaks of, with nonpositive values set to zero.
                time_array (numpy.ndarray): an array of the corresponding points in time that the signal was sampled at
                
            Returns:
                maxima_values (numpy.ndarray): an array of the calculated maximum values
                maxima_places (numpy.ndarray): an array of the corresponding calculated places where the maxima occur.
            """
            maxima_values = []
            maxima_places = []
            partitioned_arr = []
            index = 0
            #setting nonpostive values equal to zero
            while index < len( arr ) and len( partitioned_arr ) < max_num_candidates :
                #Typically the first peak of the autocorrelation is the peak representing 
                #the frequency, so max_num_candidates is most accurate when equal to 2.
                one_peak = []
                #if the signal is greater than zero than iterate through the signal until we hit the end or a nonpositive value.
                if arr[ index ] > 0:
                    while index < len( arr ) and arr[ index ] > 0:
                        one_peak.append( arr[ index ] )
                        index += 1
                    if max( one_peak ) > .2:
                        """
                        Only consider peaks where the value of the peak is greater than .2,
                        otherwise the autocorrelation of that peak is not strong enough to be 
                        considered for the maxima.
                        """
                        partitioned_arr.append( one_peak )
                else:
                    #continue iterating through the signal until we find a positive value
                    while index < len( arr ) and arr[ index ] <= 0:
                        index += 1
            for part in partitioned_arr:
                #for each segment append the maximum and the maximizer
                maxima_values.append( max( part ) )
                maxima_places.append( float( time_array[ np.argwhere( arr == max( part ) ) ] ) )
            return np.array(maxima_values), np.array(maxima_places)
        
        #initializing list of candidates for F_0
        best_cands = []
        if HNR:
            corrs_cand_vals=[]
        for index in range( len( segmented_signal ) ):
            segment = segmented_signal[ index ]
            time_begin, time_end = index * window_len, min( ( index + 1 ) * window_len, total_time )
            window_len = time_end - time_begin
            local_peak = max( abs( segment ) )
            """
            For each segment we follow the given algorithm, by
            1. Subtracting the mean of the segment
            2. Multiply the segment by the hanning window
            3. Calculate the autocorrelation of the windowed signal (r_a)
            4. Calculate the autocorrelation of the window (r_w)
            5. Divide the autocorrelation of the windowed signal by 
                autocorrelation of the window to estimate the autocorrelation of the segment (r_x)
            """
            segment = segment - segment.mean()
            segment *= np.hanning( len( segment ) )
            r_a = estimated_autocorrelation( segment )
            r_w = estimated_autocorrelation( np.hanning( len( segment ) ) )
            r_x = r_a/r_w
            
            #eliminating points in the autocorrelation that are not finite (divided by a number close to zero)
            r_x = r_x[ np.isfinite( r_x ) ]
            r_len = len( r_x )
            
            #creating an array of the points in time corresponding to our sampled autocorrelation of the signal (r_x)
            time_array = np.linspace( 0, window_len, r_len )

            #Only consider the first half of the autocorrelation because for lags longer than a half of the window length, 
            #it becomes less reliable there for signals with few periods per window
            limited_window = np.hstack( ( np.ones( int( r_len / 2 ) ), np.zeros( r_len - int( r_len / 2 ) ) ) )
            r_x = r_x * limited_window
            
            """
                Sidenote: In the algorithm it states to upsample the signal by a factor of 2 to get a 
            more accurate answer, however in practice most of the signals contain too much noise and once
            upsampled, the noise is exaggerated. By downsampling the peaks are cleaner and it becomes 
            easier to pick the best peak that represents the frequency.
            """
            #we down sample the signal using sinc_interpolation, and eliminate any nan
            down_sampled_time_array = np.linspace( 0, window_len, r_len /2 )
            vals = np.nan_to_num( sinc_interp( r_x , time_array, down_sampled_time_array ) )
            
            #eliminating values less than or equal to zero so it is easier to pick peaks
            vals = vals * ( vals > np.zeros( len( vals ) ) )
            time_array = down_sampled_time_array
            
            if len( vals.nonzero()[ 0 ] ) != 0:
                #finding maximizers, and maximums and eliminating values that don't produce a pitch in the allotted range.
                maxima_values, maxima_places = find_max( vals, time_array )
                
                max_place_possible = min( 1. / min_pitch, window_len / 2 )
                min_place_possible = 1. / max_pitch
                
                top_vals_elim = maxima_places[ maxima_places <= max_place_possible ]
                corrs_maxima_vals = maxima_values[ maxima_places <= max_place_possible ]
                
                maxima_places = top_vals_elim[ top_vals_elim >= min_place_possible ]
                maxima_values = corrs_maxima_vals[ top_vals_elim >= min_place_possible ]
                
                #we only want to consider maximum greater than voicing_threshold, otherwise autocorrelation is not strong enough here to provide accurate data
                maxima_places = maxima_places[ maxima_values > voicing_threshold ]
                maxima_values = maxima_values[ maxima_values > voicing_threshold ]
                
                """
                Here we check our list to make sure its not empty, then calculate strengths 
                based off the formula given in the algorithm, i.e. 
                R = r( tau_max ) - OctaveCost * log_2( MinimumPitch * tau_max ) (eq. 24)
                and append the strongest maxizer to our list of candidates.
                
                    Sidenote:In the algorithm given it defines a way to calculate the best candidate by iterating
                throw a list of all possible candidates for each segment and calculating the cost 
                associated with it, however assuming it takes a milisecond per iteration, there are
                4 candidates per segment and 20 segments, this would take approximately 34 years to calculate.
                Instead we find the best candidate per frame and choose the one of the candidates of highest
                value.
                """
                if len( maxima_values ) > 0:
                    """
                    By definition, the best candidate for the acoustic pitch period of a sound can be found
                    from the position of the maximum of the autocorrelation function of the sound, while
                    the degree of periodicity (the harmonics-to-noise ratio) of the sound can be found
                    from the relative height of this maximum
                    """
                    strengths = [ val - octave_cost * np.log2( min_pitch * place ) for place, val in zip( maxima_places, maxima_values ) ]
                    #next two lines include unvoiced candidate
                    maxima_places=np.hstack( ( maxima_places, 0 ) )
                    strengths.append( voicing_threshold + max( 0, 2 - ( local_peak / global_peak ) / ( silence_threshold / ( 1 + voicing_threshold ) ) ) )
                    if HNR:
                        #if we are calculating HNR we will want the maximum that corresponds to our F_0
                        #actually I'm not sure about that, will need to double check, could just be largest value in autocorrelation
                        corrs_cand_vals.append( maxima_values[ np.argmax( strengths ) ] )
                    best_cands.append( maxima_places[ np.argmax( strengths ) ] )    
        if len( best_cands ) == 0:
            #if there are no candidates that fit criteria then assume the signal is unvoiced, i.e. return 0.
            return 0
        # here we return the candidate that is in the 85th percentile, instead of the highest valued candidates, 
        # which are more often than not anomalies caused by changes in amplitude in the signal (autocorrelation
        # PDAS are very sensitive to changes in amplitudes.)
        best_candidate=sorted( best_cands )[ int( .85 * len( best_cands ) ) ]
        if HNR:
            corrs_cand_vals=np.array(corrs_cand_vals)
            best_max=corrs_cand_vals[np.argwhere(best_cands==best_candidate)[0]][0]
            # (eq. 4)
            return 10*np.log10(best_max/(1-best_max))
        
        if best_candidate == 0:
            return 0
        else:
            return 1. / best_candidate
        
        
    def get_HNR( self, min_pitch = 90, silence_threshold = .01, ):   
        """
        Compute Harmonic to Noise Ratio (HNR).
        Algorithm uses Fast Fourier Transform (FFT) to filter out values higher than the Nyquist Frequency. 
        Then it segments the signal into frames containing at least 6 periods of the minimum pitch.
        For each frame it then again uses FFT to calculate normalized autocorrelation of the signal. 
        After autocorrelation is calculated it is upsampled with sinc interpolation, and smoothed to find 
        the maxima values of the interpolation. After these values have been chosen the best candidate
        for the HNR is picked and then returned.
        This algorithm is adapted from 
        http://www.fon.hum.uva.nl/david/ba_shs/2010/Boersma_Proceedings_1993.pdf
        
        Args:
            min_pitch (float): minimum value to be returned as pitch, cannot be less than or equal to zero
            silence_threshold (float): Used to calculate strength of voiceless candidate, the higher the value
                                  the more likely the F_0 will be returned as voiceless.
            
        Returns:
            float: The HNR of the signal
            
        Raises:
            TypeError: min_pitch must be an int, and silence_threshold must be a float.
            ValueError: The minimum pitch cannot be equal or less than zero.
            ValueError: silence_threshold must be between 0 and 1.
            
        Example:
        ::
            
            from scipy.io import wavfile as wav
            rate, wave= wav.read( 'example_audio_file.wav' )
            sig = Signal( wave, rate )
            sig.get_HNR()
            
        """
        #***need to update test_Signal_Analysis to get 100% coverage***
        
        return self.get_F_0( min_pitch = min_pitch, silence_threshold = silence_threshold, HNR = True )
        
        
        #get code put up github/travis/coveralls...   
        #TODO:
        #clone repo, put on github-> goes in super ai->afx->features (in my fork, ask when ready to merge fork)
        #if everything is similar enough can be put in one class, else seperate it into different classes/files
        #travis and coveralls, he will get a key for me to put it on privately, which I don't have yet so maybe don't work on this.